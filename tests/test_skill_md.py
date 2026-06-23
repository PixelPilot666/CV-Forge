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
                       "check_fidelity.py"):
            self.assertIn(script, text, f"SKILL.md should reference {script}")

    def test_references_the_guard_docs(self):
        text = _read()
        for doc in ("tailoring-rules", "profile-schema", "resume-craft",
                    "review-rubric", "interview"):
            self.assertIn(doc, text, f"SKILL.md should point to references/{doc}.md")

    def test_states_whole_page_and_verbatim_rules(self):
        text = _read()
        self.assertTrue("整页" in text or "一页" in text, "must mention whole-page discipline")
        self.assertTrue("原样" in text or "verbatim" in text or "一字不差" in text,
                        "must mention verbatim preservation of key fields")

    def test_states_truthfulness_boundary(self):
        text = _read()
        self.assertTrue("补强" in text or "真实" in text,
                        "SKILL.md must state the truth-first boundary")


if __name__ == "__main__":
    unittest.main()
