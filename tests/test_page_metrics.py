"""Tests for scripts/page_metrics.py — PDF page count + last-page fill ratio.

The risky logic (parsing pdfinfo + pdftotext -bbox into a fill_ratio) is tested
as pure functions over captured real-tool output, so CI needs no poppler. A
skip-guarded leg exercises the real CLI when pdfinfo/pdftotext are present.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
FIX = os.path.join(ROOT, "tests", "fixtures")

import page_metrics as pm  # noqa: E402


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def _has(cmd):
    return shutil.which(cmd) is not None


# ── pure parsers ─────────────────────────────────────────────────────────────
class TestParsePdfinfo(unittest.TestCase):
    def test_parses_pages_line(self):
        text = _read("pdfinfo_1page.txt")
        self.assertEqual(pm.parse_pages(text), 1)

    def test_parses_arbitrary_page_count(self):
        self.assertEqual(pm.parse_pages("Title: x\nPages:          3\nEncrypted: no"), 3)

    def test_missing_pages_line_returns_none(self):
        self.assertIsNone(pm.parse_pages("Title: x\nEncrypted: no"))


class TestFillRatioFromBbox(unittest.TestCase):
    def test_sparse_page_below_band(self):
        xml = _read("bbox_sparse_1page.html")
        fr = pm.fill_ratio_from_bbox(xml)
        self.assertAlmostEqual(fr, 0.65, places=2)   # floor(0.6583, 2)

    def test_dense_fixture_has_high_fill_ratio(self):
        xml = _read("bbox_full_1page.html")
        fr = pm.fill_ratio_from_bbox(xml)
        self.assertTrue(0.90 <= fr <= 1.00, f"expected in band, got {fr}")

    def test_two_decimal_floor(self):
        xml = _read("bbox_sparse_1page.html")
        fr = pm.fill_ratio_from_bbox(xml)
        self.assertEqual(fr, round(int(fr * 100) / 100, 2))  # floored to 2 decimals

    def test_clamped_to_unit_interval(self):
        # a word past the bottom margin must clamp at 1.0, never exceed
        xml = ('<doc><page width="595.28" height="841.89">'
               '<word xMin="50" yMin="800" xMax="100" yMax="900">x</word>'
               '</page></doc>')
        self.assertLessEqual(pm.fill_ratio_from_bbox(xml), 1.0)

    def test_no_words_returns_none(self):
        xml = '<doc><page width="595.28" height="841.89"></page></doc>'
        self.assertIsNone(pm.fill_ratio_from_bbox(xml))

    def test_uses_last_page_only(self):
        # two pages: only the LAST page's words drive the ratio
        xml = ('<doc>'
               '<page width="595.28" height="841.89">'
               '<word xMin="50" yMin="700" xMax="100" yMax="742">a</word></page>'
               '<page width="595.28" height="841.89">'
               '<word xMin="50" yMin="100" xMax="100" yMax="120">b</word></page>'
               '</doc>')
        fr = pm.fill_ratio_from_bbox(xml)
        self.assertLess(fr, 0.20)   # last page nearly empty


# ── CLI ──────────────────────────────────────────────────────────────────────
class TestCLIToolAbsent(unittest.TestCase):
    SCRIPT = os.path.join(ROOT, "scripts", "page_metrics.py")

    def test_exit_two_when_tools_missing(self):
        # strip PATH so pdfinfo/pdftotext aren't found → §11.3 degradation, exit 2.
        # Use a real (non-PDF) file so we reach the tool-detection branch, not file-not-found.
        import tempfile
        env = dict(os.environ, PATH="/nonexistent")
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
            proc = subprocess.run(
                [sys.executable, self.SCRIPT, tf.name],
                capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 2)
        combined = proc.stdout + proc.stderr
        self.assertTrue("poppler" in combined.lower() or "install" in combined.lower()
                        or "安装" in combined)


@unittest.skipUnless(_has("pdfinfo") and _has("pdftotext"), "poppler required")
class TestCLIToolPresent(unittest.TestCase):
    SCRIPT = os.path.join(ROOT, "scripts", "page_metrics.py")

    @classmethod
    def setUpClass(cls):
        try:
            import yaml
        except ImportError:
            raise unittest.SkipTest("PyYAML required")
        if not shutil.which("tectonic") and not shutil.which("xelatex"):
            raise unittest.SkipTest("no LaTeX engine to build a sample PDF")
        import json as _json
        import tempfile
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import fill_template as ft
        cls.d = tempfile.mkdtemp()
        with open(os.path.join(ROOT, "examples", "sample-master-profile.yaml"),
                  encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        with open(os.path.join(ROOT, "examples", "sample-tailor-jd.json"),
                  encoding="utf-8") as f:
            tailor = _json.load(f)
        with open(os.path.join(ROOT, "assets", "templates", "zh-classic",
                               "resume.tex.tmpl"), encoding="utf-8") as f:
            tmpl = f.read()
        tex = ft.render(tmpl, ft.build_context(profile, tailor))
        tex_path = os.path.join(cls.d, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex)
        subprocess.run(["/bin/bash", os.path.join(ROOT, "scripts", "build_resume.sh"),
                        tex_path, "-t", os.path.join(ROOT, "assets", "templates", "zh-classic"),
                        "-o", cls.d], capture_output=True, text=True)
        cls.pdf = os.path.join(cls.d, "resume.pdf")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_emits_valid_metrics_json(self):
        if not os.path.isfile(self.pdf):
            self.skipTest("sample PDF did not build")
        proc = subprocess.run([sys.executable, self.SCRIPT, self.pdf],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["pages_int"], 1)
        self.assertTrue(0.0 <= out["fill_ratio"] <= 1.0)
        self.assertAlmostEqual(out["pages_float"], out["fill_ratio"], places=2)


if __name__ == "__main__":
    unittest.main()
