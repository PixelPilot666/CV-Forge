"""Tests for scripts/detect_engine.sh and scripts/render_pdf.sh.

These shell scripts are the only machine-environment-dependent pieces. We test:
- detect_engine.sh emits valid JSON with the expected keys
- detect_engine.sh exit code reflects availability
- render_pdf.sh fails cleanly (non-zero + install hint) when no engine on PATH
Actual PDF compilation (engine present) is exercised by the e2e smoke test, not here,
to keep unit tests fast and engine-independent.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECT = os.path.join(ROOT, "scripts", "detect_engine.sh")
RENDER = os.path.join(ROOT, "scripts", "render_pdf.sh")


class TestDetectEngine(unittest.TestCase):
    def test_outputs_valid_json_with_keys(self):
        proc = subprocess.run(["/bin/bash", DETECT], capture_output=True, text=True)
        data = json.loads(proc.stdout)
        self.assertIn("available", data)
        self.assertIn("engine", data)
        self.assertIn("candidates", data)
        self.assertIsInstance(data["candidates"], dict)

    def test_exit_code_matches_availability(self):
        proc = subprocess.run(["/bin/bash", DETECT], capture_output=True, text=True)
        data = json.loads(proc.stdout)
        if data["available"]:
            self.assertEqual(proc.returncode, 0)
        else:
            self.assertNotEqual(proc.returncode, 0)

    def test_reports_no_engine_when_path_empty(self):
        # Minimal PATH keeps bash/coreutils but excludes /opt/homebrew where tex lives.
        env = dict(os.environ)
        env["PATH"] = "/usr/bin:/bin"
        proc = subprocess.run(["/bin/bash", DETECT], capture_output=True, text=True, env=env)
        data = json.loads(proc.stdout)
        self.assertFalse(data["available"])
        self.assertNotEqual(proc.returncode, 0)


class TestRenderPdf(unittest.TestCase):
    def test_missing_engine_fails_with_install_hint(self):
        env = dict(os.environ)
        env["PATH"] = "/usr/bin:/bin"
        with tempfile.TemporaryDirectory() as d:
            tex = os.path.join(d, "x.tex")
            with open(tex, "w") as f:
                f.write("\\documentclass{article}\\begin{document}hi\\end{document}")
            proc = subprocess.run(
                ["/bin/bash", RENDER, tex, "-o", d],
                capture_output=True, text=True, env=env,
            )
            self.assertNotEqual(proc.returncode, 0)
            combined = proc.stdout + proc.stderr
            # should guide the user to install, not crash silently
            self.assertTrue("tectonic" in combined or "install" in combined.lower()
                            or "安装" in combined)

    def test_missing_input_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run(
                ["/bin/bash", RENDER, os.path.join(d, "nope.tex"), "-o", d],
                capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
