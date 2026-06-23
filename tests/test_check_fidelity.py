"""Tests for scripts/check_fidelity.py — verbatim preservation of key fields.

Guards rule A1: company/title/dates/paper-name/project-name in the tailored headings
must match the profile verbatim (no rewriting like 'Agent 工程师' -> '算法工程师').
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import check_fidelity as cf  # noqa: E402


PROFILE = {
    "basics": {"name": "刘兴宇", "phone": "185-0641-5283", "email": "a@b.com"},
    "experience": [
        {"id": "expe-1", "org": "新奥新智科技有限公司", "title": "Agent 工程师",
         "date": "2025.01 - 2026.01"},
    ],
    "projects": [
        {"id": "proj-1", "name": "多Agent选课推荐系统", "date": ""},
    ],
    "research": [
        {"id": "pub-1", "name": "Boosting the dual-stream architecture", "date": ""},
    ],
    "education": [
        {"id": "edu-1", "school": "南开大学", "date": "2024.09 - 2027.06"},
    ],
}


class TestStripLatex(unittest.TestCase):
    def test_strips_textbf_hfill(self):
        s = cf.strip_latex(r"\textbf{Agent 工程师} \hfill \textbf{新奥新智科技有限公司}")
        self.assertIn("Agent 工程师", s)
        self.assertIn("新奥新智科技有限公司", s)
        self.assertNotIn("textbf", s)


class TestFidelity(unittest.TestCase):
    def _tailor(self, heading, ref="expe-1", date="2025.01 - 2026.01"):
        return {"sections": [{"title": "实习经历", "entries": [
            {"ref": ref, "heading": heading, "date": date, "bullet_ids": []}]}]}

    def test_faithful_heading_passes(self):
        t = self._tailor(r"\textbf{Agent 工程师} \hfill \textbf{新奥新智科技有限公司}")
        violations = cf.check(PROFILE, t)
        self.assertEqual(violations, [], f"unexpected: {violations}")

    def test_rewritten_title_is_violation(self):
        # title changed to 算法工程师(推荐方向) -> must be flagged
        t = self._tailor(r"\textbf{算法工程师（推荐方向）} \hfill \textbf{新奥新智科技有限公司}")
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("Agent 工程师" in v for v in violations))

    def test_rewritten_company_is_violation(self):
        t = self._tailor(r"\textbf{Agent 工程师} \hfill \textbf{字节跳动}")
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("新奥新智科技有限公司" in v for v in violations))

    def test_changed_date_is_violation(self):
        t = self._tailor(r"\textbf{Agent 工程师} \hfill \textbf{新奥新智科技有限公司}",
                         date="2024.01 - 2026.01")
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("2025.01 - 2026.01" in v for v in violations))

    def test_project_name_must_be_verbatim(self):
        t = {"sections": [{"title": "项目经历", "entries": [
            {"ref": "proj-1", "heading": r"\textbf{多Agent推荐系统}", "date": "",
             "bullet_ids": []}]}]}  # dropped '选课'
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("多Agent选课推荐系统" in v for v in violations))

    def test_paper_name_must_be_verbatim(self):
        t = {"sections": [{"title": "科研经历", "entries": [
            {"ref": "pub-1", "heading": r"\textbf{Boosting the dual-stream architecture}（共同一作）",
             "date": "", "bullet_ids": []}]}]}
        violations = cf.check(PROFILE, t)
        self.assertEqual(violations, [], f"verbatim paper name should pass: {violations}")

    def test_unknown_ref_is_violation(self):
        t = self._tailor(r"\textbf{X}", ref="does-not-exist")
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("does-not-exist" in v for v in violations))


if __name__ == "__main__":
    unittest.main()
