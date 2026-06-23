"""Tests for scripts/fill_template.py — placeholder substitution + LaTeX escaping."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fill_template as ft  # noqa: E402


class TestLatexEscape(unittest.TestCase):
    def test_escapes_all_specials(self):
        self.assertEqual(ft.latex_escape("50%"), r"50\%")
        self.assertEqual(ft.latex_escape("a_b"), r"a\_b")
        self.assertEqual(ft.latex_escape("a&b"), r"a\&b")
        self.assertEqual(ft.latex_escape("$100"), r"\$100")
        self.assertEqual(ft.latex_escape("C#"), r"C\#")
        self.assertEqual(ft.latex_escape("{x}"), r"\{x\}")

    def test_backslash_escaped_first(self):
        # backslash must not double-process the escapes it introduces
        self.assertEqual(ft.latex_escape("a\\b"), r"a\textbackslash{}b")

    def test_tilde_and_caret(self):
        self.assertEqual(ft.latex_escape("~"), r"\textasciitilde{}")
        self.assertEqual(ft.latex_escape("^"), r"\textasciicircum{}")

    def test_plain_text_unchanged(self):
        self.assertEqual(ft.latex_escape("普通中文文本"), "普通中文文本")


class TestBoldMarkdown(unittest.TestCase):
    """`**x**` in bullet text -> \\textbf{x}, but the content is still LaTeX-escaped."""

    def test_bold_converted_after_escape(self):
        # 50% must escape to 50\%, and ** ** must become \textbf{}
        out = ft.escape_with_bold("**P@1 提升 96.7%**")
        self.assertEqual(out, r"\textbf{P@1 提升 96.7\%}")

    def test_bold_partial(self):
        out = ft.escape_with_bold("指标 **96.7%** 显著提升")
        self.assertEqual(out, r"指标 \textbf{96.7\%} 显著提升")

    def test_no_bold_plain_escape(self):
        out = ft.escape_with_bold("a_b 50%")
        self.assertEqual(out, r"a\_b 50\%")

    def test_literal_asterisk_not_paired(self):
        # a single * is not a bold marker; it should be left as-is (escaped form)
        out = ft.escape_with_bold("3 * 4 = 12")
        self.assertNotIn(r"\textbf", out)

    def test_bullet_text_uses_bold(self):
        out = ft.render("{{#bullets}}{{text}}{{/bullets}}",
                        {"bullets": [{"text": "**核心**成果"}]})
        self.assertEqual(out, r"\textbf{核心}成果")


class TestScalar(unittest.TestCase):
    def test_scalar_substitution_escapes(self):
        out = ft.render("姓名 {{name}}", {"name": "a_b"})
        self.assertEqual(out, r"姓名 a\_b")

    def test_missing_scalar_becomes_empty(self):
        out = ft.render("x{{nope}}y", {})
        self.assertEqual(out, "xy")

    def test_raw_field_not_escaped(self):
        # fields whitelisted as preformatted LaTeX pass through unescaped
        out = ft.render("{{heading}}", {"heading": r"\textbf{公司} \hfill \textbf{职位}"},
                        raw_keys={"heading"})
        self.assertEqual(out, r"\textbf{公司} \hfill \textbf{职位}")


class TestConditional(unittest.TestCase):
    def test_if_true_keeps_block(self):
        out = ft.render("{{#if photo}}有照片{{/if}}", {"photo": True})
        self.assertEqual(out, "有照片")

    def test_if_false_drops_block(self):
        out = ft.render("{{#if photo}}有照片{{/if}}", {"photo": False})
        self.assertEqual(out, "")

    def test_if_missing_drops_block(self):
        out = ft.render("a{{#if photo}}X{{/if}}b", {})
        self.assertEqual(out, "ab")


class TestLoop(unittest.TestCase):
    def test_simple_loop(self):
        tmpl = "{{#bullets}}- {{text}}\n{{/bullets}}"
        out = ft.render(tmpl, {"bullets": [{"text": "一"}, {"text": "二"}]})
        self.assertEqual(out, "- 一\n- 二\n")

    def test_loop_escapes_item_values(self):
        tmpl = "{{#bullets}}{{text}}{{/bullets}}"
        out = ft.render(tmpl, {"bullets": [{"text": "99%"}]})
        self.assertEqual(out, r"99\%")

    def test_empty_loop_renders_nothing(self):
        out = ft.render("X{{#items}}{{a}}{{/items}}Y", {"items": []})
        self.assertEqual(out, "XY")

    def test_nested_loops(self):
        tmpl = "{{#sections}}[{{title}}]{{#entries}}({{heading}}){{/entries}}{{/sections}}"
        data = {"sections": [
            {"title": "A", "entries": [{"heading": "x"}, {"heading": "y"}]},
            {"title": "B", "entries": [{"heading": "z"}]},
        ]}
        out = ft.render(tmpl, data, raw_keys={"heading"})
        self.assertEqual(out, "[A](x)(y)[B](z)")


class TestIntegration(unittest.TestCase):
    def test_full_resume_skeleton(self):
        tmpl = (
            "\\name{{{name}}}\n"
            "{{#if photo}}\\yourphoto{{{photo_size}}}{{/if}}\n"
            "{{#sections}}\\section{{{title}}}\n"
            "{{#entries}}\\datedsubsection{{{heading}}}{{{date}}}\n"
            "{{#bullets}}\\item {{text}}\n{{/bullets}}{{/entries}}{{/sections}}"
        )
        data = {
            "name": "李明", "photo": False, "photo_size": "0.12",
            "sections": [
                {"title": "实习经历", "entries": [
                    {"heading": r"\textbf{工程师}", "date": "2025",
                     "bullets": [{"text": "P@1 提升至 96.7%"}]},
                ]},
            ],
        }
        out = ft.render(tmpl, data, raw_keys={"heading", "date", "title", "photo_size"})
        self.assertIn(r"\name{李明}", out)
        self.assertNotIn("yourphoto", out)  # photo False -> dropped
        self.assertIn(r"\section{实习经历}", out)
        self.assertIn(r"\textbf{工程师}", out)  # raw heading preserved
        self.assertIn(r"96.7\%", out)          # bullet text escaped


if __name__ == "__main__":
    unittest.main()
