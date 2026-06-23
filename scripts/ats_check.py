#!/usr/bin/env python3
"""ATS 关键词命中检查: 把 JD 中的关键词与"渲染后简历的纯文本"逐项比对。

为什么对渲染后的 PDF 文本做检查: ATS(简历筛选系统)读到的是 PDF 抽取出的纯文本，
在这层检查才能反映 ATS 真正看到的内容。

用法:
    python3 scripts/ats_check.py <jd.txt> <resume.pdf|resume.txt>
    python3 scripts/ats_check.py --keywords "Python,RAG,Go" <resume.pdf>

退出码: 0 = 完成(无论命中多少)。
关键词抽取是启发式的(技术词典 + 大小写归一); 编排层(SKILL.md)会用 LLM 做更细的
JD 结构化解析, 本脚本提供确定性的命中核对底座。
"""
import argparse
import os
import re
import subprocess
import sys

# 常见技术关键词词典(可扩展)。命中后保留词典里的规范大小写。
TECH_TERMS = [
    "Python", "Go", "Golang", "Java", "C++", "C#", "JavaScript", "TypeScript", "Rust",
    "FastAPI", "Flask", "Django", "Spring", "Gin",
    "RAG", "LangChain", "LangGraph", "LlamaIndex", "Agent", "Multi-Agent",
    "FAISS", "Milvus", "Chroma", "Elasticsearch", "BGE-M3", "BM25", "RRF",
    "LoRA", "RAGAS", "DeepSeek", "Qwen", "LLM", "Embedding", "微调", "向量检索", "召回",
    "MySQL", "PostgreSQL", "Redis", "MongoDB", "Kafka", "gRPC",
    "Docker", "Kubernetes", "K8s", "CI/CD", "Linux", "AWS", "GCP",
    "PyTorch", "TensorFlow", "机器学习", "深度学习", "大模型", "检索增强",
]


def extract_keywords(jd_text):
    """从 JD 文本启发式抽取关键词(词典命中 + 大小写归一去重)。"""
    found = []
    seen = set()
    low = jd_text.lower()
    for term in TECH_TERMS:
        if term.lower() in low and term.lower() not in seen:
            found.append(term)
            seen.add(term.lower())
    return found


def check(keywords, resume_text):
    """逐个关键词检查是否出现在简历文本中(大小写不敏感)。"""
    low = resume_text.lower()
    report = []
    for kw in keywords:
        report.append({"keyword": kw, "present": kw.lower() in low})
    return report


def summarize(report):
    hit = sum(1 for r in report if r["present"])
    return {"total": len(report), "hit": hit, "miss": len(report) - hit}


def extract_text(path):
    """从 .txt / .pdf 抽取纯文本。pdf 优先用 pdftotext, 退而求其次给出提示。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".tex"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    if ext == ".pdf":
        if _has("pdftotext"):
            out = subprocess.run(["pdftotext", "-layout", path, "-"],
                                 capture_output=True, text=True)
            if out.returncode == 0:
                return out.stdout
        # 退路: 提示但不崩溃(返回空串, 让命中检查显示全 miss 而非报错)
        sys.stderr.write(
            "提示: 未找到 pdftotext，无法从 PDF 抽取文本做 ATS 核对。\n"
            "  macOS: brew install poppler；Ubuntu: apt install poppler-utils\n"
        )
        return ""
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _has(cmd):
    from shutil import which
    return which(cmd) is not None


def format_report(report, summary):
    lines = ["| 关键词 | 命中 |", "|---|---|"]
    for r in report:
        lines.append("| %s | %s |" % (r["keyword"], "✅" if r["present"] else "❌"))
    lines.append("")
    lines.append("命中 %d / %d（缺失 %d）" % (summary["hit"], summary["total"], summary["miss"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="ATS 关键词命中检查")
    parser.add_argument("jd", nargs="?", help="JD 文本文件(.txt)")
    parser.add_argument("resume", help="渲染后的简历(.pdf / .txt)")
    parser.add_argument("--keywords", help="直接给定关键词(逗号分隔)，跳过 JD 抽取")
    args = parser.parse_args(argv)

    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    elif args.jd:
        with open(args.jd, encoding="utf-8", errors="ignore") as f:
            keywords = extract_keywords(f.read())
    else:
        print("错误: 需提供 JD 文件或 --keywords", file=sys.stderr)
        return 2

    resume_text = extract_text(args.resume)
    report = check(keywords, resume_text)
    summary = summarize(report)
    print(format_report(report, summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
