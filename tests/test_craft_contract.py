"""Contract tests for JD analysis, bullet writing, and interview guidance."""
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCES = os.path.join(ROOT, "references")


def _read(name):
    with open(os.path.join(REFERENCES, name), encoding="utf-8") as f:
        return f.read()


class TestJobFocusContract(unittest.TestCase):
    def test_jd_analysis_derives_mission_and_only_three_priorities(self):
        text = _read("jd-analysis.md")
        self.assertIn("一句话岗位使命", text)
        self.assertIn("Top 3", text)
        self.assertIn("证据", text)
        self.assertIn("缺口", text)

    def test_craft_rules_define_content_budgets(self):
        text = _read("resume-craft.md")
        self.assertIn("内容预算", text)
        self.assertIn("核心要求", text)
        self.assertIn("技术清单", text)


class TestEvidenceContract(unittest.TestCase):
    def test_bullet_formula_prioritizes_action_choice_and_outcome(self):
        text = _read("resume-craft.md")
        self.assertIn("动作 + 技术选择 + 结果", text)
        self.assertIn("不是每条 bullet 都必须有数字", text)

    def test_metrics_require_explainable_context(self):
        craft = _read("resume-craft.md")
        interview = _read("interview.md")
        for term in ("口径", "基线", "评测方式"):
            self.assertIn(term, craft)
            self.assertIn(term, interview)

    def test_core_bullets_default_to_problem_method_result(self):
        text = _read("resume-craft.md")
        self.assertIn("问题 → 方法 → 结果", text)
        self.assertIn("不机械", text)
        self.assertIn("结果可以是", text)

    def test_metric_selection_prefers_explainable_outcomes_over_tuning_logs(self):
        text = _read("resume-craft.md")
        for term in ("指标对象", "样本", "调参过程", "权重"):
            self.assertIn(term, text)


class TestRoleVariantContract(unittest.TestCase):
    def test_agent_and_search_recommendation_use_distinct_evidence_lenses(self):
        text = _read("resume-craft.md")
        self.assertIn("Agent / RAG", text)
        self.assertIn("搜索 / 推荐", text)
        self.assertIn("Tool Calling", text)
        self.assertIn("CTR/CVR", text)

    def test_generic_variants_do_not_overwrite_each_other(self):
        text = _read("resume-craft.md")
        self.assertIn("独立版本", text)
        self.assertIn("覆盖", text)


class TestIdentityAndPresentationContract(unittest.TestCase):
    def test_company_display_keeps_legal_entity_and_bolds_verified_qualifier(self):
        craft = _read("resume-craft.md")
        truth = _read("tailoring-rules.md")
        for term in ("法定主体", "集团", "整体加粗"):
            self.assertIn(term, craft)
        self.assertIn("法定主体", truth)
        self.assertIn("展示性旁注", truth)

    def test_retained_research_gets_a_contribution_sentence(self):
        text = _read("resume-craft.md")
        self.assertIn("研究贡献", text)
        self.assertIn("作者位次", text)


class TestConstraintLayerContract(unittest.TestCase):
    def test_prompt_constraints_are_not_collapsed_into_runtime_guards(self):
        text = _read("resume-craft.md")
        self.assertIn("Prompt 约束", text)
        self.assertIn("运行时", text)
        self.assertIn("拒答", text)


if __name__ == "__main__":
    unittest.main()
