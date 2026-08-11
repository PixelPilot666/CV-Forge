"""Tests for scripts/polish_gate.py — the deterministic three-state polish gate.

Encodes the SPEC §11.5–§11.9 contract: page count policy, actionable classification,
strict-improvement partial order, the pass/revise/deliver-best decision table,
the deliverable formula, and exit codes 0/10/2. Pure logic — no external tools.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
FIX = os.path.join(ROOT, "tests", "fixtures")

import polish_gate as pg  # noqa: E402


def _candidate(score=28, high=0, med=0, fr=0.94, page_ok=True, pages=1):
    return {"score": score, "high_flags": high, "med_flags": med,
            "fill_ratio": fr, "page_ok": page_ok, "pages": pages}


# ── §11.3 page count hard gate + density warnings ───────────────────────────
class TestPagePolicy(unittest.TestCase):
    def test_page_count_must_match_target(self):
        self.assertTrue(pg.page_count_ok(1, 1))
        self.assertTrue(pg.page_count_ok(2, 2))
        self.assertFalse(pg.page_count_ok(2, 1))
        self.assertFalse(pg.page_count_ok(1, 2))

    def test_fill_ratio_only_produces_density_warnings(self):
        self.assertEqual(pg.density_warning(0.70), "sparse")
        self.assertIsNone(pg.density_warning(0.90))
        self.assertEqual(pg.density_warning(0.99), "dense")
        self.assertIsNone(pg.density_warning(None))


# ── §11.6 actionable classification with fallback coercion ───────────────────
class TestActionableCount(unittest.TestCase):
    def test_counts_actionable_labels(self):
        rev = {"improvements": [
            {"text": "把 X 置顶", "category": "actionable", "axis": "role_focus"},
            {"text": "删项目名", "category": "actionable", "axis": "clarity"}]}
        self.assertEqual(pg.actionable_count(rev, {"red_flags": []}), 2)

    def test_needsfact_labels_not_counted(self):
        rev = {"improvements": [
            {"text": "缺学生规模", "category": "needs-fact", "axis": "evidence"}]}
        self.assertEqual(pg.actionable_count(rev, {"red_flags": []}), 0)

    def test_high_severity_fabrication_forced_actionable(self):
        # critic mislabels a high-severity 夸大 flag as needs-fact → coerced to actionable
        critic = {"red_flags": [
            {"issue": "夸大原创性「提出」实为复现", "severity": "high",
             "category": "needs-fact", "axis": "clarity", "needs_new_fact": False}]}
        self.assertEqual(pg.actionable_count({"improvements": []}, critic), 1)

    def test_any_high_red_flag_is_actionable_before_fact_followup(self):
        critic = {"red_flags": [
            {"issue": "当前正文把未核实能力写成已上线系统", "severity": "high",
             "category": "needs-fact", "axis": "credibility", "needs_new_fact": True}]}
        self.assertEqual(pg.actionable_count({"improvements": []}, critic), 1)

    def test_needs_new_fact_flag_forced_needsfact(self):
        # labeled actionable but needs_new_fact=true → coerced to needs-fact
        rev = {"improvements": [
            {"text": "补一个真实指标", "category": "actionable", "axis": "credibility",
             "needs_new_fact": True}]}
        self.assertEqual(pg.actionable_count(rev, {"red_flags": []}), 0)

    def test_missing_number_keyword_forced_needsfact(self):
        # labeled actionable but text screams missing-data → coerced to needs-fact
        rev = {"improvements": [
            {"text": "该 bullet 缺数字，建议补充", "category": "actionable", "axis": "evidence"}]}
        self.assertEqual(pg.actionable_count(rev, {"red_flags": []}), 0)


# ── §11.7 strict-improvement partial order ───────────────────────────────────
class TestStrictlyBetter(unittest.TestCase):
    def test_null_best_is_worst(self):
        self.assertTrue(pg.strictly_better(_candidate(), None, 1))

    def test_fewer_high_flags_wins_even_if_total_lower(self):
        cand = _candidate(score=24, high=0)
        best = _candidate(score=26, high=1)
        self.assertTrue(pg.strictly_better(cand, best, 1))

    def test_more_high_flags_loses(self):
        cand = _candidate(score=29, high=1)
        best = _candidate(score=24, high=0)
        self.assertFalse(pg.strictly_better(cand, best, 1))

    def test_page_count_hard_gate_blocks_wrong_page_candidate(self):
        cand = _candidate(score=29, page_ok=False, pages=2)
        best = _candidate(score=24, page_ok=True, pages=1)
        self.assertFalse(pg.strictly_better(cand, best, 1))

    def test_high_flag_removal_overrides_page_count_gate(self):
        cand = _candidate(score=24, high=0, page_ok=False, pages=2)
        best = _candidate(score=29, high=1, page_ok=True, pages=1)
        self.assertTrue(pg.strictly_better(cand, best, 1))

    def test_med_flag_reduction_beats_total_with_same_page_status(self):
        cand = _candidate(score=24, med=0, page_ok=True)
        best = _candidate(score=26, med=1, page_ok=True)
        self.assertTrue(pg.strictly_better(cand, best, 1))

    def test_higher_total_wins_when_flags_and_page_status_tie(self):
        self.assertTrue(pg.strictly_better(_candidate(score=27), _candidate(score=25), 1))
        self.assertFalse(pg.strictly_better(_candidate(score=25), _candidate(score=27), 1))

    def test_fill_ratio_does_not_break_an_otherwise_equal_tie(self):
        cand = _candidate(score=26, fr=0.99)
        best = _candidate(score=26, fr=0.70)
        self.assertFalse(pg.strictly_better(cand, best, 1))


# ── §11.8 decide(): three-state decision table ───────────────────────────────
def _state(round=0, cal=0, last_dir="none", best=None, oscillated=False):
    return {"schema": "cv-forge/polish-state@1", "round": round, "max_rounds": 1,
            "page_target": 1, "density_warning_band": [0.75, 0.98],
            "cal": cal, "max_cal": 2,
            "fidelity_fix": 0, "max_fidelity_fix": 2, "build_retry": 0,
            "max_build_retry": 1, "last_pages": None, "last_fill_ratio": None,
            "last_dir": last_dir, "last_score": None, "last_high_flags": None,
            "has_actionable": None, "best": best, "history": [], "needs_fact": [],
            "unfixed_actionable": [], "terminated": False, "deliverable": None,
            "decision": None, "delivery_reason": None, "oscillated": oscillated}


class TestDecide(unittest.TestCase):
    def _run(self, state, metrics, reviewer, critic, n=1):
        return pg.decide(state, metrics, reviewer, critic, n)

    def test_pass_when_score_high_page_count_matches_and_no_flags(self):
        res, st = self._run(_state(), {"pages_int": 1, "fill_ratio": 0.94},
                            {"total": 28, "improvements": []}, {"red_flags": []})
        self.assertEqual(res["decision"], "pass")
        self.assertEqual(res["reason"], "pass")
        self.assertTrue(res["deliverable"])

    def test_low_hiring_axis_prevents_total_score_from_masking_a_weakness(self):
        reviewer = {
            "total": 27,
            "scores": {"role_focus": 5, "evidence": 5, "ownership": 2,
                       "credibility": 5, "impact": 5, "clarity": 5},
            "improvements": [
                {"text": "明确本人负责边界", "category": "actionable",
                 "axis": "ownership"}],
        }
        res, st = self._run(
            _state(), {"pages_int": 1, "fill_ratio": 0.94},
            reviewer, {"red_flags": []})
        self.assertEqual(res["decision"], "revise")
        self.assertFalse(res["dimension_floor_ok"])
        self.assertFalse(st["terminated"])

    def test_revise_when_actionable_and_round_budget_left(self):
        res, st = self._run(
            _state(round=0), {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 23, "improvements": [
                {"text": "把 X 置顶", "category": "actionable", "axis": "role_focus"}]},
            {"red_flags": []})
        self.assertEqual(res["decision"], "revise")
        self.assertEqual(st["round"], 1)         # state round incremented
        self.assertEqual(st["cal"], 0)           # cal reset on revise
        self.assertIsNotNone(st["best"])         # best snapshot updated on revise entry

    def test_review_round_tracks_a_fresh_review_after_revision(self):
        first, revised = self._run(
            _state(round=0), {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 23, "improvements": [
                {"text": "把 X 置顶", "category": "actionable", "axis": "role_focus"}]},
            {"red_flags": []})
        self.assertEqual(first["decision"], "revise")
        self.assertEqual(revised["round"], 1)
        self.assertEqual(revised["last_review_round"], 0)

        final, reviewed = self._run(
            revised, {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 28, "improvements": []}, {"red_flags": []})
        self.assertEqual(final["decision"], "pass")
        self.assertEqual(reviewed["last_review_round"], reviewed["round"])

    def test_terminal_selected_snapshot_matches_the_pdf_just_reviewed(self):
        old_best = _candidate(score=28, high=0, pages=1)
        old_best["round"] = 0
        final, state = self._run(
            _state(round=1, best=old_best),
            {"pages_int": 1, "fill_ratio": 0.70},
            {"total": 24, "improvements": []}, {"red_flags": []})

        self.assertEqual(final["decision"], "deliver-best")
        self.assertEqual(state["best"]["score"], 28)  # historical best is retained
        self.assertEqual(state["selected"]["round"], 1)
        self.assertEqual(state["selected"]["score"], 24)
        self.assertEqual(state["selected"]["fill_ratio"], 0.70)

    def test_only_factual_gaps_terminates_without_revise(self):
        # the headline anti-loop case: low score but every gap is needs-fact
        res, st = self._run(
            _state(round=0), {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 22, "improvements": [
                {"text": "缺学生规模", "category": "needs-fact", "axis": "evidence"}]},
            {"red_flags": []})
        self.assertEqual(res["decision"], "deliver-best")
        self.assertEqual(res["reason"], "only_factual_gaps")

    def test_max_rounds_blocks_second_revise(self):
        res, st = self._run(
            _state(round=1), {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 23, "improvements": [
                {"text": "把 X 置顶", "category": "actionable", "axis": "role_focus"}]},
            {"red_flags": []})
        self.assertEqual(res["decision"], "deliver-best")
        self.assertEqual(res["reason"], "max_rounds_reached")

    def test_sparse_one_page_is_deliverable_with_warning(self):
        res, st = self._run(
            _state(round=0), {"pages_int": 1, "fill_ratio": 0.70},
            {"total": 28, "improvements": []}, {"red_flags": []})
        self.assertEqual(res["decision"], "pass")
        self.assertEqual(res["density_warning"], "sparse")
        self.assertTrue(res["deliverable"])

    def test_wrong_page_count_is_not_deliverable(self):
        res, st = self._run(
            _state(round=0), {"pages_int": 2, "fill_ratio": 0.30,
                              "pages_float": 1.30},
            {"total": 28, "improvements": []}, {"red_flags": []})
        self.assertEqual(res["decision"], "deliver-best")
        self.assertEqual(res["reason"], "page_count_mismatch")
        self.assertFalse(res["deliverable"])

    def test_high_flag_triggers_revise_then_terminates(self):
        critic = {"red_flags": [
            {"issue": "夸大原创性", "severity": "high", "category": "actionable",
             "axis": "clarity", "needs_new_fact": False}]}
        # round 0: high flag → revise
        res0, _ = self._run(_state(round=0), {"pages_int": 1, "fill_ratio": 0.94},
                            {"total": 28, "improvements": []}, critic)
        self.assertEqual(res0["decision"], "revise")
        # round 1 with high flag still present → deliver-best, not deliverable
        res1, _ = self._run(_state(round=1), {"pages_int": 1, "fill_ratio": 0.94},
                            {"total": 28, "improvements": []}, critic)
        self.assertEqual(res1["decision"], "deliver-best")
        self.assertFalse(res1["deliverable"])

    def test_soft_floor_deliverable_below_26(self):
        # total 24 (>=SOFT_FLOOR), no flags, one page, no rounds left → deliverable true
        res, st = self._run(
            _state(round=1), {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 24, "improvements": []}, {"red_flags": []})
        self.assertEqual(res["decision"], "deliver-best")
        self.assertTrue(res["deliverable"])

    def test_below_soft_floor_not_deliverable(self):
        res, st = self._run(
            _state(round=1), {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 20, "improvements": []}, {"red_flags": []})
        self.assertEqual(res["decision"], "deliver-best")
        self.assertFalse(res["deliverable"])

    def test_oscillation_blocks_revise(self):
        res, st = self._run(
            _state(round=0, oscillated=True), {"pages_int": 1, "fill_ratio": 0.94},
            {"total": 23, "improvements": [
                {"text": "把 X 置顶", "category": "actionable", "axis": "role_focus"}]},
            {"red_flags": []})
        self.assertEqual(res["decision"], "deliver-best")
        self.assertEqual(res["reason"], "oscillation")


# ── CLI: exit codes + stdout shape + atomic state rewrite ─────────────────────
class TestCLI(unittest.TestCase):
    GATE = os.path.join(ROOT, "scripts", "polish_gate.py")

    def _invoke(self, state_name, metrics_name, review_name, critic_name, n=1):
        d = tempfile.mkdtemp()
        try:
            state = os.path.join(d, "polish-state.json")
            shutil.copy(os.path.join(FIX, state_name), state)
            proc = subprocess.run(
                [sys.executable, self.GATE, "--state", state,
                 "--metrics", os.path.join(FIX, metrics_name),
                 "--review", os.path.join(FIX, review_name),
                 "--critic", os.path.join(FIX, critic_name),
                 "--target-pages", str(n)],
                capture_output=True, text=True)
            with open(state, encoding="utf-8") as f:
                reloaded = json.load(f)
            return proc, reloaded
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_pass_exit_zero_and_stdout_shape(self):
        proc, st = self._invoke("polish_state_init.json", "metrics_inband.json",
                                "reviewer_pass.json", "critic_clean.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        for key in ("decision", "reason", "round", "total", "fill_ratio",
                    "density_warning", "page_ok", "dimension_floor_ok",
                    "high_flags", "deliverable"):
            self.assertIn(key, out)
        self.assertEqual(out["decision"], "pass")
        self.assertTrue(st["terminated"])

    def test_revise_exit_ten(self):
        proc, st = self._invoke("polish_state_init.json", "metrics_inband.json",
                                "reviewer_actionable.json", "critic_clean.json")
        self.assertEqual(proc.returncode, 10, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["decision"], "revise")
        self.assertEqual(st["round"], 1)         # state file rewritten with incremented round

    def test_deliver_best_exit_zero(self):
        proc, st = self._invoke("polish_state_init.json", "metrics_oob.json",
                                "reviewer_needsfact.json", "critic_clean.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["decision"], "deliver-best")

    def test_missing_state_exits_two(self):
        proc = subprocess.run(
            [sys.executable, self.GATE, "--state", "/nonexistent/s.json",
             "--metrics", os.path.join(FIX, "metrics_inband.json"),
             "--review", os.path.join(FIX, "reviewer_pass.json"),
             "--critic", os.path.join(FIX, "critic_clean.json"),
             "--target-pages", "1"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_missing_review_routes_to_review_unavailable(self):
        d = tempfile.mkdtemp()
        try:
            state = os.path.join(d, "s.json")
            shutil.copy(os.path.join(FIX, "polish_state_init.json"), state)
            proc = subprocess.run(
                [sys.executable, self.GATE, "--state", state,
                 "--metrics", os.path.join(FIX, "metrics_inband.json"),
                 "--review", "/nonexistent/r.json",
                 "--critic", "/nonexistent/c.json",
                 "--target-pages", "1"],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["decision"], "deliver-best")
            self.assertEqual(out["reason"], "review_unavailable")
            self.assertIsNone(out["dimension_floor_ok"])
            with open(state, encoding="utf-8") as f:
                terminal = json.load(f)
            self.assertIsNone(terminal["selected"]["score"])
            self.assertEqual(terminal["selected"]["round"], 0)
            self.assertEqual(terminal["last_pages"], 1)
            self.assertEqual(terminal["last_fill_ratio"], 0.94)
            self.assertIsNone(terminal["last_density_warning"])
            self.assertIsNone(terminal["last_score"])
            self.assertIsNone(terminal["last_high_flags"])
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
