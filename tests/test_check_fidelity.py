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
    "basics": {"name": "李明", "phone": "138-0000-0000", "email": "a@b.com"},
    "experience": [
        {"id": "expe-1", "org": "某科技有限公司", "title": "Agent 工程师",
         "date": "2025.01 - 2026.01", "bullets": [
             {"id": "expe-1-b1", "text": "在 46 条查询上将 MRR 从 0.55 提升至 0.65",
              "metrics": {"sample_size": 46, "mrr_before": 0.55, "mrr_after": 0.65}},
         ], "org_relations": [
             {"id": "expe-1-rel-group", "entity": "某集团",
              "relation_type": "group_affiliate", "evidence_type": "official_source",
              "evidence": "https://example.com/official-members", "verified_at": "2026-08-11"},
             {"id": "expe-1-rel-brand", "entity": "Demo 3D",
              "relation_type": "brand", "evidence_type": "user_confirmation",
              "evidence": "用户确认品牌名", "verified_at": "2026-08-11"},
         ]},
    ],
    "projects": [
        {"id": "proj-1", "name": "多Agent选课推荐系统", "date": ""},
    ],
    "research": [
        {"id": "pub-1", "name": "Sample Paper Title on Image Recognition", "date": ""},
    ],
    "education": [
        {"id": "edu-1", "school": "某重点大学", "date": "2024.09 - 2027.06"},
    ],
}


class TestStripLatex(unittest.TestCase):
    def test_strips_textbf_hfill(self):
        s = cf.strip_latex(r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司}")
        self.assertIn("Agent 工程师", s)
        self.assertIn("某科技有限公司", s)
        self.assertNotIn("textbf", s)


class TestFidelity(unittest.TestCase):
    def _tailor(self, heading, ref="expe-1", date="2025.01 - 2026.01"):
        return {"sections": [{"title": "实习经历", "entries": [
            {"ref": ref, "heading": heading, "date": date, "bullet_ids": []}]}]}

    def test_faithful_heading_passes(self):
        t = self._tailor(r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司}")
        violations = cf.check(PROFILE, t)
        self.assertEqual(violations, [], f"unexpected: {violations}")

    def test_rewritten_title_is_violation(self):
        # title changed to 算法工程师(推荐方向) -> must be flagged
        t = self._tailor(r"\textbf{算法工程师（推荐方向）} \hfill \textbf{某科技有限公司}")
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("Agent 工程师" in v for v in violations))

    def test_rewritten_company_is_violation(self):
        t = self._tailor(r"\textbf{Agent 工程师} \hfill \textbf{字节跳动}")
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("某科技有限公司" in v for v in violations))

    def test_changed_date_is_violation(self):
        t = self._tailor(r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司}",
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
            {"ref": "pub-1", "heading": r"\textbf{Sample Paper Title on Image Recognition}（共同一作）",
             "date": "", "bullet_ids": []}]}]}
        violations = cf.check(PROFILE, t)
        self.assertEqual(violations, [], f"verbatim paper name should pass: {violations}")

    def test_unknown_ref_is_violation(self):
        t = self._tailor(r"\textbf{X}", ref="does-not-exist")
        violations = cf.check(PROFILE, t)
        self.assertTrue(any("does-not-exist" in v for v in violations))

    def _v2_tailor(self, **entry_updates):
        entry = {
            "ref": "expe-1",
            "heading": r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司}",
            "date": "2025.01 - 2026.01",
            "intro": "负责 Agent 检索与评测链路。",
            "intro_source_ids": ["expe-1", "expe-1-b1"],
            "bullet_ids": ["expe-1-b1"],
            "bullet_overrides": {
                "expe-1-b1": "针对检索效果不足，在 46 条查询上优化召回，MRR 从 0.55 提升至 0.65"
            },
            "override_audit": {
                "expe-1-b1": {
                    "source_ids": ["expe-1-b1"],
                    "change_type": "reframe",
                    "claim_notes": "只重组问题—方法—结果，数字不变"
                }
            }
        }
        entry.update(entry_updates)
        return {"schema_version": 2, "sections": [{"title": "实习经历", "entries": [entry]}]}

    def test_v2_audited_entry_passes(self):
        self.assertEqual(cf.check(PROFILE, self._v2_tailor()), [])

    def test_v2_intro_requires_source_ids(self):
        violations = cf.check(PROFILE, self._v2_tailor(intro_source_ids=[]))
        self.assertTrue(any("intro_source_ids" in v for v in violations))

    def test_v2_intro_rejects_unknown_source(self):
        violations = cf.check(
            PROFILE, self._v2_tailor(intro_source_ids=["another-entry-b1"]))
        self.assertTrue(any("another-entry-b1" in v for v in violations))

    def test_v2_override_requires_matching_audit(self):
        violations = cf.check(PROFILE, self._v2_tailor(override_audit={}))
        self.assertTrue(any("override_audit" in v for v in violations))

    def test_v2_override_audit_requires_claim_notes(self):
        violations = cf.check(PROFILE, self._v2_tailor(override_audit={
            "expe-1-b1": {
                "source_ids": ["expe-1-b1"],
                "change_type": "reframe",
                "claim_notes": ""
            }
        }))
        self.assertTrue(any("claim_notes" in v for v in violations))

    def test_v2_override_rejects_number_absent_from_sources(self):
        violations = cf.check(PROFILE, self._v2_tailor(bullet_overrides={
            "expe-1-b1": "在 460 条查询上优化召回，MRR 从 0.55 提升至 0.65"
        }))
        self.assertTrue(any("460" in v and "新增数字" in v for v in violations))

    def test_v2_override_rejects_changed_numeric_unit(self):
        violations = cf.check(PROFILE, self._v2_tailor(bullet_overrides={
            "expe-1-b1": "在 46 万条查询上优化召回，MRR 从 0.55 提升至 0.65"
        }))
        self.assertTrue(any("46 万条" in v for v in violations))

    def test_v2_override_rejects_reversed_metric_direction(self):
        violations = cf.check(PROFILE, self._v2_tailor(bullet_overrides={
            "expe-1-b1": "在 46 条查询上优化召回，MRR 从 0.65 提升至 0.55"
        }))
        self.assertTrue(any("顺序" in v for v in violations))

    def test_v2_inline_org_note_is_rejected(self):
        violations = cf.check(PROFILE, self._v2_tailor(
            heading=r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司（某集团旗下）}",
            org_note={
                "text": "某集团旗下",
                "relation_type": "group_affiliate",
                "evidence": "",
                "verified_at": "2026-08-11"
            }))
        self.assertTrue(any("禁止内联 org_note" in v for v in violations))

    def test_v2_heading_rejects_undeclared_company_qualifier(self):
        violations = cf.check(PROFILE, self._v2_tailor(
            heading=r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司（某集团旗下）}"))
        self.assertTrue(any("未声明附加信息" in v and "某集团旗下" in v
                            for v in violations))

    def test_v2_control_word_cannot_be_disguised_as_brand_note(self):
        violations = cf.check(PROFILE, self._v2_tailor(
            heading=r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司（某集团旗下）}",
            org_note={
                "entity": "某集团",
                "text": "某集团旗下",
                "relation_type": "brand",
                "evidence_type": "user_confirmation",
                "evidence": "用户口述",
                "verified_at": "2026-08-11"
            }))
        self.assertTrue(any("禁止内联 org_note" in v for v in violations))

    def test_v2_brand_note_rejects_free_form_relationship_synonyms(self):
        for phrase in ("某集团附属企业", "某集团所属企业", "由某集团实际控制"):
            with self.subTest(phrase=phrase):
                violations = cf.check(PROFILE, self._v2_tailor(
                    heading=rf"\textbf{{Agent 工程师}} \hfill \textbf{{某科技有限公司（{phrase}）}}",
                    org_note={
                        "entity": "某集团",
                        "text": phrase,
                        "relation_type": "brand",
                        "evidence_type": "user_confirmation",
                        "evidence": "用户口述",
                        "verified_at": "2026-08-11"
                    }))
                self.assertTrue(any("禁止内联 org_note" in v for v in violations))

    def test_v2_structured_group_note_passes(self):
        tailor = self._v2_tailor(
            heading=r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司（某集团旗下）}",
            org_note_ref="expe-1-rel-group")
        self.assertEqual(cf.check(PROFILE, tailor), [])

    def test_v2_org_note_entity_rejects_relationship_injection(self):
        injected = "Demo）；由某集团实际控制（"
        violations = cf.check(PROFILE, self._v2_tailor(
            heading=rf"\textbf{{Agent 工程师}} \hfill \textbf{{某科技有限公司（品牌：{injected}）}}",
            org_note={
                "entity": injected,
                "relation_type": "brand",
                "evidence_type": "user_confirmation",
                "evidence": "用户口述",
                "verified_at": "2026-08-11"
            }))
        self.assertTrue(any("禁止内联 org_note" in v for v in violations))

    def test_v2_org_note_accepts_plain_brand_entity(self):
        tailor = self._v2_tailor(
            heading=r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司（品牌：Demo 3D）}",
            org_note_ref="expe-1-rel-brand")
        self.assertEqual(cf.check(PROFILE, tailor), [])

    def test_v2_unknown_org_note_ref_is_rejected(self):
        violations = cf.check(PROFILE, self._v2_tailor(
            heading=r"\textbf{Agent 工程师} \hfill \textbf{某科技有限公司（某集团旗下）}",
            org_note_ref="expe-1-rel-missing"))
        self.assertTrue(any("org_note_ref" in v and "未在当前条目" in v
                            for v in violations))


if __name__ == "__main__":
    unittest.main()
