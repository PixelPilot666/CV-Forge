"""Tests for scripts/validate_profile.py — master profile schema validation."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import validate_profile as vp  # noqa: E402


def _valid_profile():
    return {
        "schema_version": 1,
        "meta": {"lang": "zh", "updated": "2026-06-23"},
        "basics": {
            "name": "张三",
            "phone": "138-0000-0000",
            "email": "z@example.com",
        },
        "skills": [
            {"group": "语言", "items": [
                {"name": "Python", "evidence_refs": ["exp-a"]},
                {"name": "Go"},  # no evidence -> soft warning
            ]},
        ],
        "experience": [
            {"id": "exp-a", "org": "公司A", "title": "工程师", "date": "2025.01 - 2026.01",
             "bullets": [{"id": "exp-a-b1", "text": "做了事"}]},
        ],
        "education": [
            {"id": "edu-a", "school": "某大学", "date": "2020 - 2024"},
        ],
    }


class TestValidateProfile(unittest.TestCase):
    def test_valid_profile_passes(self):
        errors, warnings = vp.validate(_valid_profile())
        self.assertEqual(errors, [], f"unexpected errors: {errors}")

    def test_missing_basics_is_error(self):
        p = _valid_profile()
        del p["basics"]
        errors, _ = vp.validate(p)
        self.assertTrue(any("basics" in e for e in errors))

    def test_missing_required_basic_field_is_error(self):
        p = _valid_profile()
        p["basics"]["email"] = ""
        errors, _ = vp.validate(p)
        self.assertTrue(any("email" in e for e in errors))

    def test_entry_without_id_is_error(self):
        p = _valid_profile()
        del p["experience"][0]["id"]
        errors, _ = vp.validate(p)
        self.assertTrue(any("id" in e.lower() for e in errors))

    def test_duplicate_ids_is_error(self):
        p = _valid_profile()
        p["education"][0]["id"] = "exp-a"  # collide with experience id
        errors, _ = vp.validate(p)
        self.assertTrue(any("唯一" in e or "duplicate" in e.lower() for e in errors))

    def test_experience_missing_org_is_error(self):
        p = _valid_profile()
        del p["experience"][0]["org"]
        errors, _ = vp.validate(p)
        self.assertTrue(any("org" in e for e in errors))

    def test_skill_without_evidence_is_warning_not_error(self):
        p = _valid_profile()
        errors, warnings = vp.validate(p)
        self.assertEqual(errors, [])
        self.assertTrue(any("Go" in w for w in warnings))

    def test_dangling_evidence_ref_is_warning(self):
        p = _valid_profile()
        p["skills"][0]["items"][0]["evidence_refs"] = ["does-not-exist"]
        errors, warnings = vp.validate(p)
        self.assertEqual(errors, [])
        self.assertTrue(any("does-not-exist" in w for w in warnings))

    def test_duplicate_bullet_ids_is_error(self):
        p = _valid_profile()
        p["experience"][0]["bullets"].append({"id": "exp-a-b1", "text": "重复 bullet id"})
        errors, _ = vp.validate(p)
        self.assertTrue(any("exp-a-b1" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
