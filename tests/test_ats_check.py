"""Tests for scripts/ats_check.py — keyword hit-check against rendered resume text."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ats_check as ac  # noqa: E402


class TestKeywordExtraction(unittest.TestCase):
    def test_extracts_known_tech_terms(self):
        jd = "我们需要熟悉 Python、FastAPI 和 RAG 的工程师，了解 Kubernetes 优先。"
        kws = ac.extract_keywords(jd)
        for k in ("Python", "FastAPI", "RAG", "Kubernetes"):
            self.assertIn(k, kws)

    def test_dedup_case_insensitive(self):
        jd = "python PYTHON Python"
        kws = ac.extract_keywords(jd)
        # collapses to a single canonical entry
        lowered = [k.lower() for k in kws]
        self.assertEqual(lowered.count("python"), 1)


class TestHitCheck(unittest.TestCase):
    def test_hit_and_miss(self):
        resume = "构建了基于 Python 和 FastAPI 的 RAG 系统"
        keywords = ["Python", "FastAPI", "RAG", "Kubernetes", "Go"]
        report = ac.check(keywords, resume)
        hits = {r["keyword"]: r["present"] for r in report}
        self.assertTrue(hits["Python"])
        self.assertTrue(hits["FastAPI"])
        self.assertTrue(hits["RAG"])
        self.assertFalse(hits["Kubernetes"])
        self.assertFalse(hits["Go"])

    def test_case_insensitive_match(self):
        report = ac.check(["python"], "我用 PYTHON 写代码")
        self.assertTrue(report[0]["present"])

    def test_summary_counts(self):
        report = ac.check(["A", "B", "C"], "only A here")
        summary = ac.summarize(report)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["hit"], 1)
        self.assertEqual(summary["miss"], 2)


class TestPdfText(unittest.TestCase):
    def test_plain_text_passthrough(self):
        # .txt input returns content directly (no external tool)
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("hello RAG world")
            path = f.name
        try:
            text = ac.extract_text(path)
            self.assertIn("RAG", text)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
