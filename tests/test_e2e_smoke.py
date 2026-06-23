"""End-to-end smoke test: profile + JD-tailored tailor.json -> tex -> (PDF) + ATS report.

Verifies the full pipeline wires together and that every rendered bullet traces back to
the profile (no fabrication). PDF compilation runs only if a LaTeX engine is present;
otherwise that leg is skipped (kept env-independent for CI).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fill_template as ft  # noqa: E402
import ats_check as ac  # noqa: E402

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


def _engine_available():
    return any(shutil.which(e) for e in ("tectonic", "xelatex", "latexmk"))


@unittest.skipUnless(HAVE_YAML, "PyYAML required")
class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = yaml.safe_load(
            open(os.path.join(ROOT, "examples", "sample-master-profile.yaml"), encoding="utf-8"))
        cls.tailor = json.load(
            open(os.path.join(ROOT, "examples", "sample-tailor-jd.json"), encoding="utf-8"))
        tmpl = open(os.path.join(ROOT, "assets", "templates", "zh-classic",
                                 "resume.tex.tmpl"), encoding="utf-8").read()
        ctx = ft.build_context(cls.profile, cls.tailor)
        cls.tex = ft.render(tmpl, ctx)

    def _all_profile_bullet_texts(self):
        texts = {}
        for sect in ("experience", "projects", "research", "education"):
            for entry in self.profile.get(sect, []) or []:
                for b in entry.get("bullets", []) or []:
                    texts[b["id"]] = b["text"]
        return texts

    def test_every_rendered_bullet_traces_to_profile(self):
        """No fabrication: each selected bullet id exists in the profile."""
        known = self._all_profile_bullet_texts()
        for section in self.tailor["sections"]:
            for entry in section["entries"]:
                for bid in entry.get("bullet_ids", []):
                    self.assertIn(bid, known, f"bullet {bid} not in profile (fabrication!)")

    def test_tex_contains_core_content(self):
        self.assertIn("\\name{", self.tex)
        self.assertIn("\\section{", self.tex)
        self.assertIn("\\begin{itemize}", self.tex)

    def test_ats_keywords_hit_against_rendered_text(self):
        """A JD-aware tailoring should hit the key tech keywords in the rendered tex."""
        kws = ac.extract_keywords(
            open(os.path.join(ROOT, "examples", "sample-jd.txt"), encoding="utf-8").read())
        report = ac.check(kws, self.tex)
        summary = ac.summarize(report)
        # tailoring keeps tech-stack bullets -> expect a healthy hit rate
        self.assertGreaterEqual(summary["hit"], 10,
                                f"too few ATS hits: {summary}")

    @unittest.skipUnless(_engine_available(), "no LaTeX engine")
    def test_compiles_to_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            # stage template assets + tex
            src = os.path.join(ROOT, "assets", "templates", "zh-classic")
            for name in os.listdir(src):
                s = os.path.join(src, name)
                dst = os.path.join(d, name)
                if os.path.isdir(s):
                    shutil.copytree(s, dst)
                else:
                    shutil.copy(s, dst)
            tex_path = os.path.join(d, "resume.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(self.tex)
            proc = subprocess.run(
                ["/bin/bash", os.path.join(ROOT, "scripts", "render_pdf.sh"),
                 tex_path, "-o", d],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(os.path.isfile(os.path.join(d, "resume.pdf")))


if __name__ == "__main__":
    unittest.main()
