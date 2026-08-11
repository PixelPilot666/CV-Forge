"""Sanity tests for SKILL.md — frontmatter validity and workflow wiring."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "SKILL.md")


def _read():
    with open(SKILL, encoding="utf-8") as f:
        return f.read()


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None


class TestSkillFrontmatter(unittest.TestCase):
    def test_skill_md_exists(self):
        self.assertTrue(os.path.isfile(SKILL))

    def test_has_yaml_frontmatter(self):
        fm = _frontmatter(_read())
        self.assertIsNotNone(fm, "SKILL.md must start with --- YAML frontmatter ---")

    def test_frontmatter_has_name_and_description(self):
        import yaml
        fm = yaml.safe_load(_frontmatter(_read()))
        self.assertIn("name", fm)
        self.assertIn("description", fm)
        self.assertTrue(fm["name"])
        # description should mention triggers so the skill is discoverable
        desc = fm["description"]
        self.assertTrue(len(desc) > 30, "description too short to trigger reliably")
        self.assertTrue(any(t in desc for t in ("简历", "resume", "JD", "职位")))

    def test_name_is_kebab(self):
        import yaml
        fm = yaml.safe_load(_frontmatter(_read()))
        self.assertRegex(fm["name"], r"^[a-z0-9-]+$")


class TestWorkflowWiring(unittest.TestCase):
    def test_references_the_pipeline_scripts(self):
        text = _read()
        for script in ("extract_profile.py", "validate_profile.py", "fill_template.py",
                       "detect_engine.sh", "render_pdf.sh", "ats_check.py",
                       "check_fidelity.py", "page_metrics.py", "polish_gate.py"):
            self.assertIn(script, text, f"SKILL.md should reference {script}")

    def test_final_delivery_is_machine_finalized_after_fresh_review(self):
        text = _read()
        self.assertIn("finalize_delivery.py", text)
        self.assertIn("重新生成", text)
        self.assertIn("不得复用上一轮", text)
        self.assertIn("delivery-summary.json", text)

    def test_no_unbounded_polish_loop(self):
        # §11 supersedes the old open loop; this exact wording must be gone
        text = _read()
        self.assertNotIn("直到接近整页且铺满", text,
                         "SKILL.md must not keep the unbounded page-calibration loop")

    def test_polish_loop_is_bounded_and_gated(self):
        text = _read()
        self.assertIn("§11", text, "SKILL.md must point at the SPEC §11 bounded loop")
        self.assertIn("polish-state.json", text,
                      "SKILL.md must mention the state file that bounds the loop")

    def test_references_the_guard_docs(self):
        text = _read()
        for doc in ("tailoring-rules", "profile-schema", "resume-craft",
                    "review-rubric", "interview", "review-agent", "profile-update"):
            self.assertIn(doc, text, f"SKILL.md should point to references/{doc}.md")

    def test_review_must_be_independent_subagent(self):
        text = _read()
        self.assertTrue("子 agent" in text or "子agent" in text or "sub-agent" in text,
                        "review must be delegated to a sub-agent")
        self.assertTrue("自评" in text or "不得自评" in text,
                        "must state that the generating agent does not self-score")

    def test_states_whole_page_and_verbatim_rules(self):
        text = _read()
        self.assertTrue(any(term in text for term in ("整页", "一页", "单页")),
                        "must mention one-page discipline")
        self.assertTrue("原样" in text or "verbatim" in text or "一字不差" in text,
                        "must mention verbatim preservation of key fields")

    def test_page_count_is_hard_but_density_is_only_a_warning(self):
        text = _read()
        self.assertIn("页数是硬约束", text)
        self.assertIn("填充率只作提示", text)
        self.assertIn("不得为了填页", text)

    def test_states_truthfulness_boundary(self):
        text = _read()
        self.assertTrue("补强" in text or "真实" in text,
                        "SKILL.md must state the truth-first boundary")

    def test_generic_resume_flow_selects_a_role_family_and_preserves_variants(self):
        text = _read()
        self.assertIn("通用简历", text)
        self.assertIn("岗位族", text)
        self.assertIn("独立输出目录", text)

    def test_target_company_alias_collision_requires_confirmation(self):
        text = _read()
        self.assertIn("公司别名", text)
        self.assertIn("关联品牌", text)
        self.assertIn("主动询问", text)

    def test_final_layout_requires_visual_inspection_after_metrics(self):
        text = _read()
        self.assertIn("视觉检查", text)
        self.assertIn("日期", text)
        self.assertIn("重叠", text)

    def test_page_metrics_are_persisted_for_the_gate(self):
        text = _read()
        self.assertIn('> "$OUT/page_metrics.json"', text)

    def test_role_portrait_and_layout_audit_are_persisted(self):
        text = _read()
        self.assertIn("target-role.json", text)
        self.assertIn("layout-check.json", text)


if __name__ == "__main__":
    unittest.main()
