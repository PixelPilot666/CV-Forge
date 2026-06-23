#!/usr/bin/env python3
"""填充模板: 占位符替换 + LaTeX 转义。

支持语法(见 references/template-guide.md):
    {{key}}                标量替换(默认 LaTeX 转义)
    {{#list}}…{{/list}}    列表循环
    {{#if key}}…{{/if}}    条件块
    {{^key}}…{{/key}}      反向块(key 为假/空时渲染)

用法:
    python3 scripts/fill_template.py <profile.yaml> <tailor.json> -o resume.tex

注: 命令行入口把 master-profile + tailor.json 组装成模板上下文; 核心 render()
可独立测试。raw_keys 中的字段按"已格式化 LaTeX"原样输出, 不转义。
"""
import argparse
import re
import sys

# 默认按"已格式化 LaTeX 片段"处理、不转义的字段(由编排层拼装好排版)
DEFAULT_RAW_KEYS = {"heading", "date", "title", "photo_size", "tech_line"}
# 这些字段转义后还支持 **粗体** 标记(bullet 正文安全加粗)
DEFAULT_BOLD_KEYS = {"text"}

_SPECIALS = [
    ("\\", r"\textbackslash{}"),  # 必须最先处理
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
]


def latex_escape(s):
    """转义 LaTeX 特殊字符。反斜杠先行, 避免二次处理它引入的转义。"""
    if s is None:
        return ""
    s = str(s)
    # 先处理反斜杠: 用占位符避免它命中后续规则引入的反斜杠
    placeholder = "\x00BS\x00"
    s = s.replace("\\", placeholder)
    for ch, rep in _SPECIALS[1:]:
        s = s.replace(ch, rep)
    s = s.replace(placeholder, r"\textbackslash{}")
    return s


# 成对的 **粗体** 标记: 用于 bullet 正文安全加粗(内容仍被转义)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)


def escape_with_bold(s):
    """先 LaTeX 转义, 再把成对的 **文本** 转成 \\textbf{文本}。

    `*` 不是 LaTeX 特殊字符, 转义后仍保留, 因此可安全地在转义之后识别成对标记。
    单个未成对的 * 不受影响(原样保留)。
    """
    if s is None:
        return ""
    escaped = latex_escape(s)
    return _BOLD_RE.sub(lambda m: r"\textbf{" + m.group(1) + "}", escaped)


# --- 解析: 把模板切成 token 流, 再递归渲染 ---
# token: ('text', str) | ('var', name) | ('open', kind, name) | ('close', name)
_TOKEN_RE = re.compile(
    r"\{\{(?P<open>#if\s+\w+|#\w+|\^\w+)\}\}"
    r"|\{\{(?P<close>/\w+|/if)\}\}"
    r"|\{\{(?P<var>\w+)\}\}"
)


def _tokenize(tmpl):
    tokens = []
    pos = 0
    for m in _TOKEN_RE.finditer(tmpl):
        if m.start() > pos:
            tokens.append(("text", tmpl[pos:m.start()]))
        if m.group("open"):
            raw = m.group("open")
            if raw.startswith("#if"):
                tokens.append(("open", "if", raw.split()[1]))
            elif raw.startswith("^"):
                tokens.append(("open", "inv", raw[1:]))
            else:  # #name
                tokens.append(("open", "section", raw[1:]))
        elif m.group("close"):
            raw = m.group("close")
            name = "if" if raw == "/if" else raw[1:]
            tokens.append(("close", name))
        elif m.group("var"):
            tokens.append(("var", m.group("var")))
        pos = m.end()
    if pos < len(tmpl):
        tokens.append(("text", tmpl[pos:]))
    return tokens


def _parse(tokens, i=0, stop=None):
    """递归构建节点树, 返回 (nodes, next_index)。"""
    nodes = []
    while i < len(tokens):
        tok = tokens[i]
        if tok[0] == "close":
            return nodes, i  # 交给上层匹配
        if tok[0] == "text":
            nodes.append(tok)
            i += 1
        elif tok[0] == "var":
            nodes.append(tok)
            i += 1
        elif tok[0] == "open":
            kind, name = tok[1], tok[2]
            children, j = _parse(tokens, i + 1)
            # tokens[j] 应为对应 close
            nodes.append(("block", kind, name, children))
            i = j + 1
        else:
            i += 1
    return nodes, i


def _truthy(v):
    if isinstance(v, (list, tuple, dict, str)):
        return len(v) > 0
    return bool(v)


def _render_nodes(nodes, ctx, raw_keys, bold_keys):
    out = []
    for node in nodes:
        if node[0] == "text":
            out.append(node[1])
        elif node[0] == "var":
            name = node[1]
            val = ctx.get(name, "")
            if name in raw_keys:
                out.append("" if val is None else str(val))
            elif name in bold_keys:
                out.append(escape_with_bold(val))
            else:
                out.append(latex_escape(val))
        elif node[0] == "block":
            _, kind, name, children = node
            val = ctx.get(name)
            if kind == "if":
                if _truthy(val):
                    out.append(_render_nodes(children, ctx, raw_keys, bold_keys))
            elif kind == "inv":
                if not _truthy(val):
                    out.append(_render_nodes(children, ctx, raw_keys, bold_keys))
            elif kind == "section":
                if isinstance(val, list):
                    for item in val:
                        child_ctx = dict(ctx)
                        if isinstance(item, dict):
                            child_ctx.update(item)
                        else:
                            child_ctx = {"_": item}
                        out.append(_render_nodes(children, child_ctx, raw_keys, bold_keys))
                elif _truthy(val):
                    # 非列表真值 -> 当作单次渲染(可携带 dict 字段)
                    child_ctx = dict(ctx)
                    if isinstance(val, dict):
                        child_ctx.update(val)
                    out.append(_render_nodes(children, child_ctx, raw_keys, bold_keys))
    return "".join(out)


def render(tmpl, context, raw_keys=None, bold_keys=None):
    """渲染模板字符串。context 为 dict; raw_keys 不转义; bold_keys 转义后支持 **粗体**。"""
    if raw_keys is None:
        raw_keys = DEFAULT_RAW_KEYS
    if bold_keys is None:
        bold_keys = DEFAULT_BOLD_KEYS
    tokens = _tokenize(tmpl)
    nodes, _ = _parse(tokens)
    return _render_nodes(nodes, context, raw_keys, bold_keys)


# --- 命令行: profile + tailor.json -> 模板上下文 ---
def build_context(profile, tailor):
    """把 master-profile 与 tailor.json(裁剪结果) 组装为 zh-classic 模板上下文。

    tailor.json 结构:
        {
          "sections": [
            {"title": "实习经历",
             "entries": [
               {"ref": "expe-rag",            # 指向 profile 条目 id
                "heading": "\\textbf{...} \\hfill \\textbf{...}",  # 已排版
                "date": "2025.01 - 2026.01",
                "bullet_ids": ["expe-rag-b1", "expe-rag-b3"],  # 选用的 bullet
                "bullet_overrides": {"expe-rag-b1": "改写后的文案"}  # 可选, 润色
               }
             ]}
          ]
        }
    所有 bullet 文本最终来自 profile(或 overrides), 保证可追溯、不凭空生成。
    """
    basics = profile.get("basics", {})
    ctx = {
        "name": basics.get("name", ""),
        "phone": basics.get("phone", ""),
        "email": basics.get("email", ""),
        "photo": bool(basics.get("photo", False)),
        "photo_size": basics.get("photo_size", 0.12),
    }
    # 建立 bullet id -> text 与 entry id -> tech 索引
    bullet_text = {}
    entry_tech = {}
    for sect in ("experience", "projects", "research", "education"):
        for entry in profile.get(sect, []) or []:
            entry_tech[entry.get("id")] = entry.get("tech") or []
            for b in entry.get("bullets", []) or []:
                bullet_text[b["id"]] = b.get("text", "")

    sections = []
    for s in tailor.get("sections", []):
        entries = []
        for e in s.get("entries", []):
            overrides = e.get("bullet_overrides", {})
            bullets = []
            for bid in e.get("bullet_ids", []):
                text = overrides.get(bid, bullet_text.get(bid, ""))
                if text:
                    bullets.append({"text": text})
            # 技术栈行: 优先用 tailor 显式给的 tech_line, 否则从 profile 的 tech 拼装。
            # 防重复: 若选中的 bullet 自身已是「技术栈」行, 则不再自动生成, 避免出现两行。
            tech_line = e.get("tech_line", "")
            bullet_has_tech = any(b["text"].lstrip().startswith("技术栈") for b in bullets)
            if not tech_line and not bullet_has_tech and e.get("show_tech", True):
                tech = entry_tech.get(e.get("ref"), [])
                if tech:
                    # tech 项是纯文本, 逐个转义后用 LaTeX 的 \textbf 标签包住"技术栈"
                    items = " · ".join(latex_escape(t) for t in tech)
                    tech_line = r"\textbf{技术栈}：" + items
            entries.append({
                "heading": e.get("heading", ""),
                "date": e.get("date", ""),
                "tech_line": tech_line,
                "bullets": bullets,
                "has_items": bool(tech_line or bullets),
            })
        sections.append({"title": s.get("title", ""), "entries": entries})
    ctx["sections"] = sections
    return ctx


def main(argv=None):
    parser = argparse.ArgumentParser(description="填充简历模板")
    parser.add_argument("profile", help="master-profile.yaml")
    parser.add_argument("tailor", help="tailor.json (裁剪结果)")
    parser.add_argument("-t", "--template",
                        default="assets/templates/zh-classic/resume.tex.tmpl",
                        help="模板文件路径")
    parser.add_argument("-o", "--output", help="输出 .tex 路径(缺省 stdout)")
    args = parser.parse_args(argv)

    import json
    try:
        import yaml
    except ImportError:
        print("错误: 需要 PyYAML，请先 pip install -r requirements.txt", file=sys.stderr)
        return 2

    with open(args.profile, encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    with open(args.tailor, encoding="utf-8") as f:
        tailor = json.load(f)
    with open(args.template, encoding="utf-8") as f:
        tmpl = f.read()

    ctx = build_context(profile, tailor)
    out = render(tmpl, ctx)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"✅ 已生成 {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
