"""Contract tests for the review docs after the SPEC §11 schema extension.

The polish gate (scripts/polish_gate.py) reads a `category` field off every
reviewer improvement and critic red_flag to count actionable findings. These
substring contracts keep references/review-agent.md and review-rubric.md aligned
with what the gate parses, and confirm the §11 supersession is documented.
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "references", "review-agent.md")
RUBRIC = os.path.join(ROOT, "references", "review-rubric.md")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
HIRING_AXES = {
    "role_focus", "evidence", "ownership", "credibility", "impact", "clarity"
}


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _json_blocks(text):
    return re.findall(r"```json\n(.*?)\n```", text, re.S)


class TestReviewAgentSchema(unittest.TestCase):
    def setUp(self):
        self.text = _read(AGENT)
        self.blocks = _json_blocks(self.text)

    def test_has_reviewer_and_critic_json_examples(self):
        self.assertGreaterEqual(len(self.blocks), 2,
                                "review-agent.md must show reviewer + critic JSON")

    def test_schema_carries_category_and_axis(self):
        # both machine fields the gate's classification relies on must be documented
        self.assertIn("category", self.text)
        self.assertIn("axis", self.text)
        self.assertIn("actionable", self.text)
        self.assertIn("needs-fact", self.text)

    def test_critic_schema_carries_severity_and_needs_new_fact(self):
        self.assertIn("severity", self.text)
        self.assertIn("needs_new_fact", self.text)

    def test_at_least_one_json_example_parses_with_category(self):
        # find a block whose improvements/red_flags entries are objects carrying category
        found = False
        for b in self.blocks:
            try:
                obj = json.loads(b)
            except json.JSONDecodeError:
                continue
            items = (obj.get("improvements") or []) + (obj.get("red_flags") or [])
            if items and all(isinstance(it, dict) and "category" in it for it in items):
                found = True
                break
        self.assertTrue(found, "need a parseable JSON example with category-tagged items")

    def test_reviewer_scores_only_the_six_hiring_axes(self):
        reviewer = next(
            json.loads(block) for block in self.blocks
            if "scores" in json.loads(block)
        )
        self.assertEqual(set(reviewer["scores"]), HIRING_AXES)
        self.assertEqual(sum(reviewer["scores"].values()), reviewer["total"])
        self.assertNotIn("ats", reviewer["scores"])
        self.assertNotIn("layout", reviewer["scores"])

    def test_critic_explicitly_checks_three_known_failure_modes(self):
        for phrase in ("指标口径", "Demo 包装", "组件清单"):
            self.assertIn(phrase, self.text)

    def test_critic_checks_recent_resume_failure_modes(self):
        for phrase in ("问题—方法—结果", "Prompt 约束", "公司法定主体", "调参过程"):
            self.assertIn(phrase, self.text)

    def test_reviewer_fixtures_follow_the_current_axis_contract(self):
        for name in ("reviewer_pass.json", "reviewer_actionable.json",
                     "reviewer_needsfact.json"):
            with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
                reviewer = json.load(f)
            self.assertEqual(set(reviewer["scores"]), HIRING_AXES, name)
            self.assertEqual(sum(reviewer["scores"].values()), reviewer["total"], name)

    def test_states_gate_counts_field_not_agent(self):
        # §11.6 hard rule: polish_gate counts category; the generating agent does not reclassify
        self.assertIn("polish_gate", self.text)
        self.assertTrue("§11" in self.text or "SPEC §11" in self.text,
                        "must cross-reference SPEC §11 as the authority")

    def test_no_longer_hardcodes_unbounded_iteration_as_authority(self):
        # the old "自动迭代一轮…最多迭代 1 轮" prose must defer to §11, not stand alone
        if "最多迭代 1 轮" in self.text:
            # if the phrase survives, it must be in a context that points to §11
            self.assertIn("§11", self.text)

    def test_documents_actual_gate_exit_codes(self):
        self.assertRegex(self.text, r"0\s*=\s*终止")
        self.assertRegex(self.text, r"10\s*=\s*revise")
        self.assertRegex(self.text, r"2\s*=\s*输入缺失/异常")

    def test_high_fabrication_is_removed_before_needs_fact_followup(self):
        self.assertIn("删除或降级", self.text)
        self.assertIn("不得进入正式 PDF", self.text)


class TestReviewRubric(unittest.TestCase):
    def setUp(self):
        self.text = _read(RUBRIC)

    def test_reinterprets_thresholds_via_section_11(self):
        self.assertTrue("§11" in self.text or "polish_gate" in self.text,
                        "rubric thresholds must defer to the §11 gate")

    def test_mentions_soft_floor(self):
        # SOFT_FLOOR=24 tier introduced by §11.5/§11.8
        self.assertIn("24", self.text)

    def test_ats_and_layout_are_separate_checks_not_scored_axes(self):
        self.assertIn("独立检查", self.text)
        self.assertIn("不计入 30 分", self.text)
        axes_table = self.text.split("## 六个维度", 1)[1].split("##", 1)[0]
        self.assertNotIn("ATS 友好", axes_table)
        self.assertNotIn("页面纪律", axes_table)

    def test_evidence_axis_requires_problem_method_result(self):
        self.assertIn("问题", self.text)
        self.assertIn("方法", self.text)
        self.assertIn("结果", self.text)


if __name__ == "__main__":
    unittest.main()
