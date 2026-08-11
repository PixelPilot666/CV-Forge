"""End-to-end wiring test for the SPEC §11 polish loop.

Drives scripts/polish_gate.py exactly as SKILL.md §6 orchestration would, across
the worst-case inputs, and asserts the loop always reaches a terminating decision
within MAX_ROUNDS — the whole point of §11. The pure-gate legs need no external
tools (CI-safe); a skip-guarded leg runs page_metrics.py on a real build.
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
GATE = os.path.join(ROOT, "scripts", "polish_gate.py")

import polish_gate as pg  # noqa: E402
import finalize_delivery as fd  # noqa: E402


def _has(cmd):
    return shutil.which(cmd) is not None


def _fresh_state(d):
    s = os.path.join(d, "polish-state.json")
    shutil.copy(os.path.join(FIX, "polish_state_init.json"), s)
    return s


def _run_gate(state, metrics, review, critic, n=1):
    proc = subprocess.run(
        [sys.executable, GATE, "--state", state,
         "--metrics", os.path.join(FIX, metrics),
         "--review", os.path.join(FIX, review),
         "--critic", os.path.join(FIX, critic), "--target-pages", str(n)],
        capture_output=True, text=True)
    return proc, json.loads(proc.stdout)


class TestLoopAlwaysTerminates(unittest.TestCase):
    """For any input the loop reaches pass or deliver-best within MAX_ROUNDS rounds."""

    def _drive_to_termination(self, metrics, review, critic, n=1, max_iters=5):
        """Simulate the SKILL.md loop: gate → (revise→rerun) → … until exit 0."""
        d = tempfile.mkdtemp()
        try:
            state = _fresh_state(d)
            decisions = []
            for _ in range(max_iters):
                proc, out = _run_gate(state, metrics, review, critic, n)
                decisions.append((proc.returncode, out["decision"]))
                if proc.returncode == 0:           # terminating decision
                    return decisions, out, state
                # exit 10 = revise: SKILL.md reruns BUILD→REVIEW with the same gate.
                # The state file now has round incremented, so next call must converge.
            self.fail(f"loop did not terminate within {max_iters} iters: {decisions}")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_only_factual_gaps_terminates_immediately(self):
        # the headline anti-loop case: low score, every gap needs real data
        decisions, out, _ = self._drive_to_termination(
            "metrics_inband.json", "reviewer_needsfact.json", "critic_clean.json")
        self.assertEqual(out["decision"], "deliver-best")
        self.assertEqual(out["reason"], "only_factual_gaps")
        self.assertEqual(len(decisions), 1)        # no wasted revise round

    def test_actionable_then_terminates_within_one_round(self):
        # actionable findings → one revise (exit 10), then must terminate
        decisions, out, _ = self._drive_to_termination(
            "metrics_inband.json", "reviewer_actionable.json", "critic_clean.json")
        codes = [c for c, _ in decisions]
        self.assertIn(10, codes, "actionable findings should trigger one revise")
        self.assertEqual(codes[-1], 0, "loop must end on a terminating decision")
        self.assertLessEqual(codes.count(10), 1, "revise capped at MAX_ROUNDS=1")

    def test_pass_terminates_immediately(self):
        decisions, out, _ = self._drive_to_termination(
            "metrics_inband.json", "reviewer_pass.json", "critic_clean.json")
        self.assertEqual(out["decision"], "pass")
        self.assertTrue(out["deliverable"])

    def test_high_flag_loop_terminates_not_deliverable(self):
        # high red_flag present in both rounds → revise once, then deliver-best,
        # and the result must NOT be marked deliverable (P6/P8)
        decisions, out, _ = self._drive_to_termination(
            "metrics_inband.json", "reviewer_pass.json", "critic_high_flag.json")
        self.assertEqual(out["decision"], "deliver-best")
        self.assertFalse(out["deliverable"])

    def test_sparse_low_score_resume_terminates_without_layout_loop(self):
        decisions, out, _ = self._drive_to_termination(
            "metrics_oob.json", "reviewer_needsfact.json", "critic_clean.json")
        self.assertEqual(out["decision"], "deliver-best")
        self.assertEqual(out["density_warning"], "sparse")
        self.assertFalse(out["deliverable"])       # score 22, not density, blocks formal

    def test_sparse_one_page_can_pass_without_filler(self):
        decisions, out, _ = self._drive_to_termination(
            "metrics_oob.json", "reviewer_pass.json", "critic_clean.json")
        self.assertEqual(out["decision"], "pass")
        self.assertEqual(out["density_warning"], "sparse")
        self.assertTrue(out["deliverable"])

    def test_revision_is_draft_until_the_revised_pdf_gets_a_new_review(self):
        with tempfile.TemporaryDirectory() as d:
            state_path = _fresh_state(d)
            first, first_out = _run_gate(
                state_path, "metrics_inband.json", "reviewer_actionable.json",
                "critic_clean.json")
            self.assertEqual(first.returncode, 10)
            self.assertEqual(first_out["decision"], "revise")

            pdf_path = os.path.join(d, "resume.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"first pdf")
            with open(state_path, encoding="utf-8") as f:
                revise_state = json.load(f)
            premature = fd.finalize(revise_state, pdf_path, d)
            self.assertEqual(premature["file"], "resume.DRAFT.pdf")

            # Simulate BUILD plus a genuinely new REVIEW for round 1.
            with open(pdf_path, "wb") as f:
                f.write(b"revised pdf")
            second, second_out = _run_gate(
                state_path, "metrics_inband.json", "reviewer_pass.json",
                "critic_clean.json")
            self.assertEqual(second.returncode, 0)
            self.assertEqual(second_out["decision"], "pass")
            with open(state_path, encoding="utf-8") as f:
                terminal_state = json.load(f)

            final = fd.finalize(terminal_state, pdf_path, d)
            self.assertEqual(final["file"], "resume.pdf")
            self.assertTrue(final["formal"])
            self.assertFalse(os.path.exists(os.path.join(d, "resume.DRAFT.pdf")))


@unittest.skipUnless(_has("pdfinfo") and _has("pdftotext"), "poppler required")
class TestMetricsFeedGate(unittest.TestCase):
    """page_metrics.py output is shaped exactly as polish_gate.py --metrics consumes."""

    def test_metrics_json_drives_gate(self):
        if not (_has("tectonic") or _has("xelatex")):
            self.skipTest("no LaTeX engine")
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML required")
        import fill_template as ft
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(ROOT, "examples", "sample-master-profile.yaml"),
                      encoding="utf-8") as f:
                profile = yaml.safe_load(f)
            with open(os.path.join(ROOT, "examples", "generic-agent-tailor.json"),
                      encoding="utf-8") as f:
                tailor = json.load(f)
            fidelity = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "check_fidelity.py"),
                 os.path.join(ROOT, "examples", "sample-master-profile.yaml"),
                 os.path.join(ROOT, "examples", "generic-agent-tailor.json")],
                capture_output=True, text=True)
            self.assertEqual(fidelity.returncode, 0, fidelity.stdout + fidelity.stderr)
            with open(os.path.join(ROOT, "assets", "templates", "zh-classic",
                                   "resume.tex.tmpl"), encoding="utf-8") as f:
                tmpl = f.read()
            tex_path = os.path.join(d, "resume.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(ft.render(tmpl, ft.build_context(profile, tailor)))
            subprocess.run(["/bin/bash", os.path.join(ROOT, "scripts", "build_resume.sh"),
                            tex_path, "-t", os.path.join(ROOT, "assets", "templates", "zh-classic"),
                            "-o", d], capture_output=True, text=True)
            pdf = os.path.join(d, "resume.pdf")
            if not os.path.isfile(pdf):
                self.skipTest("sample PDF did not build")
            # real metrics → write to a file → feed the gate
            mproc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "page_metrics.py"), pdf],
                capture_output=True, text=True)
            self.assertEqual(mproc.returncode, 0, mproc.stderr)
            metrics_path = os.path.join(d, "metrics.json")
            with open(metrics_path, "w", encoding="utf-8") as f:
                f.write(mproc.stdout)
            state = _fresh_state(d)
            gproc = subprocess.run(
                [sys.executable, GATE, "--state", state, "--metrics", metrics_path,
                 "--review", os.path.join(FIX, "reviewer_pass.json"),
                 "--critic", os.path.join(FIX, "critic_clean.json"), "--target-pages", "1"],
                capture_output=True, text=True)
            self.assertEqual(gproc.returncode, 0, gproc.stderr)
            decision = json.loads(gproc.stdout)
            self.assertEqual(decision["decision"], "pass")
            with open(state, encoding="utf-8") as f:
                terminal_state = json.load(f)
            delivery = fd.finalize(terminal_state, pdf, d)
            self.assertTrue(delivery["formal"])
            self.assertEqual(delivery["file"], "resume.pdf")
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
