#!/usr/bin/env python3
"""从现有的 LaTeX 简历(resume.tex)抽取结构化 master-profile。

用法:
    python3 scripts/extract_profile.py myCV__agent_/resume.tex -o data/master-profile.yaml

抽取是启发式的: 解析 \\name / \\contactInfo / \\yourphoto, 以及
\\section{} + \\datedsubsection{标题}{日期} + itemize \\item 结构。
已知中文 section 名映射到 typed 列表(education/experience/projects/research),
其余归入 experience 作兜底。结果是"草稿", 需用户确认补充。

schema 见 references/profile-schema.md。
"""
import argparse
import re
import sys

# 已知中文章节名 -> profile 中的 typed key
SECTION_MAP = {
    "教育经历": "education",
    "教育背景": "education",
    "实习经历": "experience",
    "工作经历": "experience",
    "项目经历": "projects",
    "项目经验": "projects",
    "科研经历": "research",
    "论文": "research",
    "研究经历": "research",
}
# 每类 section 条目里, heading 解析出的主名称放到哪个字段
SECTION_NAME_FIELD = {
    "education": "school",
    "experience": "org",
    "projects": "name",
    "research": "name",
}


def latex_unescape(s):
    """把常见 LaTeX 转义/标记还原为纯文本(抽取时用, 与填充时的转义相反)。"""
    if not s:
        return ""
    # 去掉 \href{url}{text} -> text (并把 url 记录留给调用方时可扩展; 这里取显示文本)
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    # 去掉 \textbf{...}\textit{...}\emph{...} 等包裹, 保留内容
    for cmd in ("textbf", "textit", "emph", "texttt", "underline"):
        s = re.sub(r"\\%s\{([^{}]*)\}" % cmd, r"\1", s)
    # \hfill -> 空格
    s = s.replace(r"\hfill", " ")
    # 常见转义字符还原
    replacements = {
        r"\%": "%", r"\&": "&", r"\$": "$", r"\#": "#",
        r"\_": "_", r"\{": "{", r"\}": "}",
        r"\textbackslash{}": "\\",
        r"\textasciitilde{}": "~", r"\textasciicircum{}": "^",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    # 折叠多余空白
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_comments(tex):
    """删除以未转义 % 开头(或行内未转义 %)的注释。"""
    out_lines = []
    for line in tex.splitlines():
        # 找到第一个未被 \ 转义的 %
        result = []
        i = 0
        while i < len(line):
            c = line[i]
            if c == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            result.append(c)
            i += 1
        out_lines.append("".join(result))
    return "\n".join(out_lines)


def _slugify(text, fallback):
    """从中文/英文标题生成 ascii-ish 的稳定 id 片段。"""
    # 取英文/数字片段
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    if ascii_part:
        return ascii_part[:24]
    return fallback


def parse_tex(tex):
    tex = _strip_comments(tex)

    profile = {
        "schema_version": 1,
        "meta": {"lang": "zh"},
        "basics": {},
    }

    # --- basics ---
    m = re.search(r"\\name\{(.+?)\}", tex)
    if m:
        profile["basics"]["name"] = latex_unescape(m.group(1))
    m = re.search(r"\\contactInfo\{(.+?)\}\{(.+?)\}", tex)
    if m:
        profile["basics"]["phone"] = latex_unescape(m.group(1))
        profile["basics"]["email"] = latex_unescape(m.group(2))
    m = re.search(r"\\yourphoto\{([\d.]+)\}", tex)
    if m:
        profile["basics"]["photo"] = True
        profile["basics"]["photo_size"] = float(m.group(1))

    # --- sections ---
    # 抓正文部分
    body_m = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", tex, re.S)
    body = body_m.group(1) if body_m else tex

    # 按 \section{...} 切分
    section_iter = list(re.finditer(r"\\section\{(.+?)\}", body))
    seen_ids = set()

    for si, sm in enumerate(section_iter):
        title = latex_unescape(sm.group(1))
        start = sm.end()
        end = section_iter[si + 1].start() if si + 1 < len(section_iter) else len(body)
        chunk = body[start:end]

        kind = SECTION_MAP.get(title, "experience")
        name_field = SECTION_NAME_FIELD[kind]
        profile.setdefault(kind, [])

        # 在 chunk 内按 \datedsubsection 切分条目
        ds_iter = list(re.finditer(
            r"\\datedsubsection\{(.*?)\}\{(.*?)\}", chunk, re.S))
        for di, dm in enumerate(ds_iter):
            heading_raw = dm.group(1)
            date = latex_unescape(dm.group(2))
            heading = latex_unescape(heading_raw)
            # experience 标题常为 "职位 \hfill 单位"，拆成 title + org 两字段
            title_part = None
            if kind == "experience" and r"\hfill" in heading_raw:
                left, _, right = heading_raw.partition(r"\hfill")
                title_part = latex_unescape(left)
                heading = latex_unescape(right)  # 单位作为 org
            d_start = dm.end()
            d_end = ds_iter[di + 1].start() if di + 1 < len(ds_iter) else len(chunk)
            entry_body = chunk[d_start:d_end]

            # 生成稳定 id
            base = "%s-%s" % (kind[:4], _slugify(heading, "%d" % (di + 1)))
            eid = base
            n = 2
            while eid in seen_ids:
                eid = "%s-%d" % (base, n)
                n += 1
            seen_ids.add(eid)

            entry = {"id": eid, name_field: heading, "date": date}
            if title_part:
                entry["title"] = title_part

            # bullets: itemize 内的 \item
            bullets = []
            item_iter = list(re.finditer(r"\\item\s+(.*?)(?=\\item|\\end\{itemize\}|$)",
                                         entry_body, re.S))
            for bi, im in enumerate(item_iter):
                text = latex_unescape(im.group(1))
                if not text:
                    continue
                bullets.append({"id": "%s-b%d" % (eid, bi + 1), "text": text})
            if bullets:
                entry["bullets"] = bullets
            profile[kind].append(entry)

    return profile


def main(argv=None):
    parser = argparse.ArgumentParser(description="从 LaTeX 简历抽取 master-profile")
    parser.add_argument("tex", help="resume.tex 路径")
    parser.add_argument("-o", "--output", help="输出 YAML 路径(缺省打印到 stdout)")
    args = parser.parse_args(argv)

    try:
        with open(args.tex, encoding="utf-8") as f:
            tex = f.read()
    except FileNotFoundError:
        print(f"错误: 找不到文件 {args.tex}", file=sys.stderr)
        return 2

    profile = parse_tex(tex)

    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _deps import dump_yaml

    try:
        out = dump_yaml(profile)
    except ImportError:
        return 2
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"✅ 已抽取到 {args.output}（这是草稿，请确认并补充）", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
