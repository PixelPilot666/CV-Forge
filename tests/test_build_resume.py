"""Tests for scripts/build_resume.sh — the temp-dir compile that keeps output lean.

build_resume.sh stages template assets (fonts/cls/sty/images) in a throwaway dir,
compiles there, and copies only resume.pdf (+ the editable resume.tex) back to $OUT.
This keeps each application's output dir at ~tens of KB instead of ~43MB of fonts.

Compilation needs a LaTeX engine, so the end-to-end leg is skipped when none is on
PATH. The leanness contract (no fonts/sty copied to $OUT) is asserted whenever the
build succeeds.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "scripts", "build_resume.sh")
TMPL = os.path.join(ROOT, "assets", "templates", "zh-classic")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fill_template as ft  # noqa: E402

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


def _engine_available():
    return any(shutil.which(e) for e in ("tectonic", "xelatex", "latexmk"))


def _render_example_tex(out_dir):
    profile = yaml.safe_load(
        open(os.path.join(ROOT, "examples", "sample-master-profile.yaml"), encoding="utf-8"))
    tailor = json.load(
        open(os.path.join(ROOT, "examples", "sample-tailor-jd.json"), encoding="utf-8"))
    tmpl = open(os.path.join(TMPL, "resume.tex.tmpl"), encoding="utf-8").read()
    tex = ft.render(tmpl, ft.build_context(profile, tailor))
    tex_path = os.path.join(out_dir, "resume.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex)
    return tex_path


class TestBuildResumeArgs(unittest.TestCase):
    def test_missing_input_fails(self):
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run(
                ["/bin/bash", BUILD, os.path.join(d, "nope.tex"), "-t", TMPL, "-o", d],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)

    def test_missing_template_dir_fails(self):
        with tempfile.TemporaryDirectory() as d:
            tex = os.path.join(d, "x.tex")
            open(tex, "w").write("\\documentclass{article}\\begin{document}hi\\end{document}")
            proc = subprocess.run(
                ["/bin/bash", BUILD, tex, "-t", os.path.join(d, "no-such-tmpl"), "-o", d],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)


@unittest.skipUnless(HAVE_YAML, "PyYAML required")
@unittest.skipUnless(_engine_available(), "no LaTeX engine")
class TestBuildResumeEndToEnd(unittest.TestCase):
    def test_produces_pdf_and_keeps_output_lean(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "cv-forge", "示例-岗位-zh-test")
            os.makedirs(out)
            tex_path = _render_example_tex(out)
            proc = subprocess.run(
                ["/bin/bash", BUILD, tex_path, "-t", TMPL, "-o", out],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            names = set(os.listdir(out))
            # the deliverable is there
            self.assertIn("resume.pdf", names)
            self.assertIn("resume.tex", names)
            # leanness contract: heavy template assets must NOT land in the output dir
            self.assertNotIn("fonts", names, "fonts/ leaked into output dir (bloat!)")
            self.assertFalse([n for n in names if n.endswith(".sty")],
                             f".sty files leaked into output dir: {names}")
            self.assertFalse([n for n in names if n.endswith(".cls")],
                             f".cls leaked into output dir: {names}")
            # whole output dir should be small (no embedded font dir)
            total = sum(os.path.getsize(os.path.join(out, n)) for n in names
                        if os.path.isfile(os.path.join(out, n)))
            self.assertLess(total, 5 * 1024 * 1024,
                            f"output dir unexpectedly large ({total} bytes)")


if __name__ == "__main__":
    unittest.main()
