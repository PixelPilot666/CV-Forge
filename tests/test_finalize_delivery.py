"""Regression tests for formal-vs-draft delivery finalization."""
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import finalize_delivery as fd  # noqa: E402


def _state(decision="pass", terminated=True, deliverable=True, score=28,
           high_flags=0, round_=0, last_review_round=0):
    return {
        "round": round_,
        "last_review_round": last_review_round,
        "terminated": terminated,
        "decision": decision,
        "deliverable": deliverable,
        "delivery_reason": "pass" if decision == "pass" else "max_rounds_reached",
        "page_target": 1,
        "best": {"score": score, "high_flags": high_flags,
                 "pages": 1, "page_ok": True},
    }


class TestDeliveryEligibility(unittest.TestCase):
    def test_only_reviewed_terminal_deliverable_state_is_formal(self):
        self.assertTrue(fd.is_formal_delivery(_state()))

    def test_revise_state_is_never_formal(self):
        state = _state(decision="revise", terminated=False, deliverable=False,
                       score=23, high_flags=1, round_=1, last_review_round=0)
        self.assertFalse(fd.is_formal_delivery(state))

    def test_high_flag_overrides_inconsistent_deliverable_true(self):
        self.assertFalse(fd.is_formal_delivery(_state(high_flags=1)))

    def test_revision_without_a_new_review_is_not_formal(self):
        state = _state(round_=1, last_review_round=0)
        self.assertFalse(fd.is_formal_delivery(state))

    def test_wrong_page_count_overrides_inconsistent_deliverable_true(self):
        state = _state()
        state["best"]["pages"] = 2
        state["best"]["page_ok"] = False
        self.assertFalse(fd.is_formal_delivery(state))

    def test_selected_snapshot_controls_delivery_instead_of_historical_best(self):
        state = _state()
        state["selected"] = {"score": 23, "high_flags": 1,
                             "pages": 1, "page_ok": True}
        self.assertFalse(fd.is_formal_delivery(state))


class TestFinalize(unittest.TestCase):
    def test_formal_delivery_uses_resume_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            source = os.path.join(d, "candidate.pdf")
            with open(source, "wb") as f:
                f.write(b"pdf")
            summary = fd.finalize(_state(), source, d)
            self.assertEqual(summary["file"], "resume.pdf")
            self.assertTrue(summary["formal"])
            self.assertTrue(os.path.isfile(os.path.join(d, "resume.pdf")))

    def test_current_23_point_high_flag_revise_bug_becomes_draft(self):
        with tempfile.TemporaryDirectory() as d:
            source = os.path.join(d, "resume.pdf")
            with open(source, "wb") as f:
                f.write(b"pdf")
            state = _state(decision="revise", terminated=False, deliverable=False,
                           score=23, high_flags=1, round_=1, last_review_round=0)

            summary = fd.finalize(state, source, d)

            self.assertEqual(summary["file"], "resume.DRAFT.pdf")
            self.assertEqual(summary["score"], 23)
            self.assertEqual(summary["high_flags"], 1)
            self.assertFalse(os.path.exists(os.path.join(d, "resume.pdf")))
            self.assertTrue(os.path.isfile(os.path.join(d, "resume.DRAFT.pdf")))

    def test_summary_uses_selected_snapshot_not_historical_best(self):
        with tempfile.TemporaryDirectory() as d:
            source = os.path.join(d, "candidate.pdf")
            with open(source, "wb") as f:
                f.write(b"pdf")
            state = _state()
            state["selected"] = {"score": 23, "high_flags": 1,
                                 "pages": 1, "page_ok": True}

            summary = fd.finalize(state, source, d)

            self.assertEqual(summary["score"], 23)
            self.assertEqual(summary["high_flags"], 1)
            self.assertEqual(summary["file"], "resume.DRAFT.pdf")

    def test_cli_emits_report_ready_gate_fields(self):
        with tempfile.TemporaryDirectory() as d:
            state_path = os.path.join(d, "polish-state.json")
            pdf_path = os.path.join(d, "candidate.pdf")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(_state(decision="deliver-best", score=24), f)
            with open(pdf_path, "wb") as f:
                f.write(b"pdf")

            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "finalize_delivery.py"),
                 "--state", state_path, "--pdf", pdf_path, "--out-dir", d],
                capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = json.loads(proc.stdout)
            for key in ("decision", "deliverable", "delivery_reason", "score",
                        "high_flags", "page_ok", "density_warning", "file", "formal"):
                self.assertIn(key, summary)

    def test_cli_rejects_non_object_state(self):
        with tempfile.TemporaryDirectory() as d:
            state_path = os.path.join(d, "polish-state.json")
            pdf_path = os.path.join(d, "candidate.pdf")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            with open(pdf_path, "wb") as f:
                f.write(b"pdf")

            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "finalize_delivery.py"),
                 "--state", state_path, "--pdf", pdf_path, "--out-dir", d],
                capture_output=True, text=True)

            self.assertEqual(proc.returncode, 2)
            self.assertFalse(os.path.exists(os.path.join(d, "resume.pdf")))


if __name__ == "__main__":
    unittest.main()
