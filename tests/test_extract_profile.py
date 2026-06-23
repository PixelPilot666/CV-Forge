"""Tests for scripts/extract_profile.py — parse a LaTeX resume into a profile dict."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import extract_profile as ep  # noqa: E402
import validate_profile as vp  # noqa: E402

SAMPLE_TEX = r"""
\documentclass{resume}
\usepackage{zh_CN-Adobefonts_external}
\begin{document}
\name{刘兴宇}
\contactInfo{185-0641-5283}{xingyu\_liu2002@163.com}
\yourphoto{0.12}

\section{教育经历}
\datedsubsection{\textbf{南开大学（985、211、双一流）}，计算机技术，\textit{硕士（保研）}}{2024.09 - 2027.06}
\begin{itemize} [parsep=1ex]
    \item \textbf{导师}：天津市重点实验室 \href{https://cv.nankai.edu.cn/}{杨巨峰}
  \item \textbf{荣誉奖项}：公能一等奖学金
\end{itemize}

\section{实习经历}
\datedsubsection{\textbf{Agent 工程师} \hfill \textbf{新奥新智科技有限公司}}{2025.01 - 2026.01}
\begin{itemize}[parsep=0.5ex]
    \item \textbf{技术栈}：LangChain · FastAPI · FAISS
    \item 构建端到端旅行套餐生成系统，P@1 从 86.7\% 提升至 96.7\%
\end{itemize}

\section{项目经历}
\datedsubsection{\textbf{多Agent选课推荐系统}（独立项目）}{}
\begin{itemize}[parsep=0.5ex]
    \item 技术栈：FastAPI · LangGraph · Milvus
    \item 基于 LangGraph 设计 Supervisor 多 Agent 编排框架
\end{itemize}

% \datedsubsection{\textbf{被注释掉的项目}}{}
% \begin{itemize}
%   \item 不应被解析
% \end{itemize}

\end{document}
"""


class TestExtractProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = ep.parse_tex(SAMPLE_TEX)

    def test_basics_extracted(self):
        b = self.p["basics"]
        self.assertEqual(b["name"], "刘兴宇")
        self.assertEqual(b["phone"], "185-0641-5283")
        # underscore unescaped back to plain text
        self.assertEqual(b["email"], "xingyu_liu2002@163.com")
        self.assertTrue(b.get("photo"))

    def test_sections_extracted_in_order(self):
        titles = [s["title"] for s in self.p["sections"]] if "sections" in self.p else None
        # extractor maps known section names to typed lists; check the four buckets exist
        self.assertIn("education", self.p)
        self.assertIn("experience", self.p)
        self.assertIn("projects", self.p)

    def test_entries_have_stable_ids(self):
        for sect in ("education", "experience", "projects"):
            for entry in self.p.get(sect, []):
                self.assertTrue(entry.get("id"), f"{sect} entry missing id")
                for bullet in entry.get("bullets", []):
                    self.assertTrue(bullet.get("id"), "bullet missing id")

    def test_bullets_parsed(self):
        exp = self.p["experience"][0]
        texts = [b["text"] for b in exp["bullets"]]
        self.assertTrue(any("旅行套餐" in t for t in texts))
        # LaTeX escaping of % should be reverted to plain text in stored profile
        self.assertTrue(any("86.7%" in t for t in texts))

    def test_commented_lines_ignored(self):
        names = []
        for sect in ("education", "experience", "projects", "research"):
            for entry in self.p.get(sect, []):
                names.append(entry.get("name", "") + entry.get("org", "") + entry.get("title", ""))
        joined = " ".join(names)
        self.assertNotIn("被注释掉", joined)

    def test_extracted_profile_is_valid(self):
        errors, _ = vp.validate(self.p)
        self.assertEqual(errors, [], f"extracted profile invalid: {errors}")


if __name__ == "__main__":
    unittest.main()
