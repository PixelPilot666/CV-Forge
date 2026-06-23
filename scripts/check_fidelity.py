#!/usr/bin/env python3
"""保真检查: 确保裁剪结果 (tailor.json) 中的关键字段与 master profile 一字不差。

守护 resume-craft.md 的硬规则 A1: 公司名 / 岗位名 / 起止时间 / 论文名 / 项目名
必须 verbatim, 不得改写 (例如把「Agent 工程师」改成「算法工程师(推荐方向)」)。

用法:
    python3 scripts/check_fidelity.py data/master-profile.yaml tailor.json
退出码: 0 = 全部保真; 1 = 存在违规(逐条打印)。
"""
import argparse
import re
import sys

# 各 section 中"必须在 heading 里 verbatim 出现"的字段
VERBATIM_FIELDS = {
    "experience": ["title", "org"],
    "projects": ["name"],
    "research": ["name"],
    "education": ["school"],
}


def strip_latex(s):
    """去掉常见 LaTeX 排版命令, 取出可读文本, 便于做 verbatim 子串比对。"""
    if not s:
        return ""
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    for cmd in ("textbf", "textit", "emph", "texttt", "underline"):
        s = re.sub(r"\\%s\{([^{}]*)\}" % cmd, r"\1", s)
    s = s.replace(r"\hfill", " ")
    s = re.sub(r"\\[a-zA-Z]+\b", " ", s)   # 其余命令
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _index(profile):
    idx = {}
    for section, fields in VERBATIM_FIELDS.items():
        for entry in profile.get(section, []) or []:
            idx[entry.get("id")] = (section, entry)
    return idx


def check(profile, tailor):
    """返回违规字符串列表(空 = 全部保真)。"""
    violations = []
    idx = _index(profile)

    for s in tailor.get("sections", []):
        for e in s.get("entries", []):
            ref = e.get("ref")
            if ref not in idx:
                violations.append(
                    f"裁剪条目引用了不存在的 profile id「{ref}」(无法核对保真性)")
                continue
            section, entry = idx[ref]
            heading_text = strip_latex(e.get("heading", ""))

            # 关键字段必须在 heading 中 verbatim 出现
            for field in VERBATIM_FIELDS[section]:
                expected = (entry.get(field) or "").strip()
                if not expected:
                    continue
                if expected not in heading_text:
                    violations.append(
                        f"[{ref}] {field}「{expected}」被改写或缺失："
                        f"heading 实际为「{heading_text}」")

            # 时间必须与 profile 一致(profile 有非空 date 时)
            prof_date = (entry.get("date") or "").strip()
            if prof_date:
                tailor_date = (e.get("date") or "").strip()
                if tailor_date != prof_date:
                    violations.append(
                        f"[{ref}] 时间被改写：profile「{prof_date}」≠ tailor「{tailor_date}」")

    return violations


def _load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path):
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description="保真检查: 关键字段必须 verbatim")
    parser.add_argument("profile", help="master-profile.yaml")
    parser.add_argument("tailor", help="tailor.json")
    args = parser.parse_args(argv)

    try:
        profile = _load_yaml(args.profile)
        tailor = _load_json(args.tailor)
    except ImportError:
        print("错误: 需要 PyYAML，请先 pip install -r requirements.txt", file=sys.stderr)
        return 2
    except FileNotFoundError as ex:
        print(f"错误: {ex}", file=sys.stderr)
        return 2

    violations = check(profile, tailor)
    if violations:
        print("❌ 保真检查未通过（关键信息必须与素材库一字不差）：", file=sys.stderr)
        for v in violations:
            print(f"  • {v}", file=sys.stderr)
        return 1
    print("✅ 保真检查通过：公司/岗位/时间/论文名/项目名均与素材库一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
