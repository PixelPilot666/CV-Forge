"""Sanitized regression fixture for a generic Agent role."""
import json
import os
import sys
import unittest

import yaml


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fill_template as ft  # noqa: E402


class TestGenericAgentFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "examples", "generic-agent-expected-analysis.json"),
                  encoding="utf-8") as f:
            cls.analysis = json.load(f)
        with open(os.path.join(ROOT, "examples", "generic-agent-tailor.json"),
                  encoding="utf-8") as f:
            cls.tailor = json.load(f)
        with open(os.path.join(ROOT, "examples", "sample-master-profile.yaml"),
                  encoding="utf-8") as f:
            cls.profile = yaml.safe_load(f)

    def test_agent_workflow_is_the_mission_and_rag_is_supporting_evidence(self):
        self.assertIn("Agent", self.analysis["mission"])
        self.assertIn("开发者工具", self.analysis["mission"])
        self.assertEqual(len(self.analysis["top_requirements"]), 3)
        self.assertNotIn("RAG", self.analysis["mission"])
        self.assertIn("RAG", self.analysis["supporting_evidence"])

    def test_every_expected_requirement_has_profile_evidence_or_an_explicit_gap(self):
        profile_ids = {
            bullet["id"]
            for section in ("education", "experience", "projects", "research")
            for entry in self.profile.get(section, [])
            for bullet in entry.get("bullets", [])
        }
        for requirement in self.analysis["top_requirements"]:
            self.assertTrue(requirement["evidence_refs"] or requirement["gap"])
            for evidence_ref in requirement["evidence_refs"]:
                self.assertIn(evidence_ref, profile_ids)

    def test_sanitized_tailor_renders_with_fewer_evidence_led_bullets(self):
        template_path = os.path.join(
            ROOT, "assets", "templates", "zh-classic", "resume.tex.tmpl")
        with open(template_path, encoding="utf-8") as f:
            rendered = ft.render(
                f.read(), ft.build_context(self.profile, self.tailor))

        self.assertIn("Agent 工作流", rendered)
        self.assertIn("独立项目", rendered)
        selected = sum(
            len(entry.get("bullet_ids", []))
            for section in self.tailor["sections"]
            for entry in section["entries"]
        )
        self.assertLessEqual(selected, 8)

    def test_core_overrides_make_problem_method_result_visible(self):
        overrides = " ".join(
            text
            for section in self.tailor["sections"]
            for entry in section["entries"]
            for text in entry.get("bullet_overrides", {}).values()
        )
        for phrase in ("为解决", "采用", "提升"):
            self.assertIn(phrase, overrides)
        self.assertIn("问题—方法—结果", self.tailor["_note"])


if __name__ == "__main__":
    unittest.main()
