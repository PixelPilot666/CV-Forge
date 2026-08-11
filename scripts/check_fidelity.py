#!/usr/bin/env python3
"""保真检查: 校验关键字段原样保留，并审计 v2 裁剪改写的事实来源。

守护 resume-craft.md 的硬规则 A1: 公司名 / 岗位名 / 起止时间 / 论文名 / 项目名
必须 verbatim, 不得改写 (例如把「Agent 工程师」改成「算法工程师(推荐方向)」)。

用法:
    python3 scripts/check_fidelity.py data/master-profile.yaml tailor.json
v2 tailor 还要求 intro / bullet_overrides 显式声明同条目来源，且不得新增
来源中没有的数字；公司关系旁注必须携带结构化证据。

退出码: 0 = 全部保真; 1 = 存在违规(逐条打印)。
"""
import argparse
import json
import re
import sys

from _org_relation import display as _org_note_display
from _org_relation import validation_errors as _org_relation_errors

# 各 section 中"必须在 heading 里 verbatim 出现"的字段
VERBATIM_FIELDS = {
    "experience": ["title", "org"],
    "projects": ["name"],
    "research": ["name"],
    "education": ["school"],
}

ALLOWED_CHANGE_TYPES = {"reframe", "compress", "merge"}
NUMERIC_FACT_RE = re.compile(
    r"(?<![\w.])\d+(?:\.\d+)?\s*(?:个百分点|万条|千条|万元|亿元|"
    r"tokens?|qps|GB|MB|KB|pp|ms|分钟|小时|城市|字符|美元|条|秒|天|"
    r"个|次|人|张|篇|页|元|倍|项|组|轮|类|座|台|字|份|家|s|%|万|亿)?\+?",
    re.IGNORECASE,
)


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


def _bullet_index(entry):
    return {
        bullet.get("id"): bullet
        for bullet in entry.get("bullets", []) or []
        if bullet.get("id")
    }


def _numbers(value):
    """抽取可见数字 token；用于发现改写中新造的样本量/指标。"""
    return set(re.findall(r"\d+(?:\.\d+)?%?", str(value or "")))


def _numeric_facts(value):
    """按正文顺序提取“数字+单位”；保留顺序用于防止调换基线与结果。"""
    facts = []
    for match in NUMERIC_FACT_RE.finditer(str(value or "")):
        display = match.group(0).strip()
        key = re.sub(r"\s+", "", display).lower()
        facts.append((key, display))
    return facts


def _dedupe_facts(facts):
    seen = set()
    result = []
    for fact in facts:
        if fact[0] not in seen:
            seen.add(fact[0])
            result.append(fact)
    return result


def _is_ordered_subsequence(candidate, source):
    source_pos = 0
    for fact, _display in candidate:
        while source_pos < len(source) and source[source_pos][0] != fact:
            source_pos += 1
        if source_pos == len(source):
            return False
        source_pos += 1
    return True


def _source_text(entry, bullet_idx, source_ids):
    parts = []
    for source_id in source_ids:
        if source_id == entry.get("id"):
            parts.extend(str(entry.get(key, "")) for key in
                         ("org", "title", "role", "summary", "date"))
            parts.append(json.dumps(entry.get("metrics", {}), ensure_ascii=False))
            continue
        bullet = bullet_idx.get(source_id)
        if bullet:
            parts.append(str(bullet.get("text", "")))
            parts.append(json.dumps(bullet.get("metrics", {}), ensure_ascii=False))
    return " ".join(parts)


def _check_new_numbers(ref, field_name, rendered_text, source_text, violations):
    source_numbers = _numbers(source_text)
    for token in sorted(_numbers(rendered_text) - source_numbers):
        violations.append(
            f"[{ref}] {field_name} 新增数字「{token}」，声明来源中未出现")
    rendered_facts = _numeric_facts(rendered_text)
    source_facts = _dedupe_facts(_numeric_facts(source_text))
    if rendered_facts and not _is_ordered_subsequence(rendered_facts, source_facts):
        rendered_display = " → ".join(display for _key, display in rendered_facts)
        source_display = " → ".join(display for _key, display in source_facts)
        violations.append(
            f"[{ref}] {field_name} 的数字/单位顺序与来源不一致："
            f"改写「{rendered_display}」；来源「{source_display}」")


def _heading_residual(entry, tailored, org_relation=None):
    residual = strip_latex(tailored.get("heading", ""))
    for value in (entry.get("title"), entry.get("org")):
        if value:
            residual = residual.replace(str(value), "", 1)
    note_display = _org_note_display(org_relation)
    if note_display:
        residual = residual.replace(note_display, "", 1)
    return re.sub(r"[\s()（）\[\]【】,，.。·|｜:：;；/\\\-—]+", "", residual)


def _org_relation_index(entry):
    return {
        relation.get("id"): relation
        for relation in entry.get("org_relations", []) or []
        if isinstance(relation, dict) and relation.get("id")
    }


def _check_org_relation(ref, relation, violations):
    relation_id = relation.get("id", "?")
    prefix = f"[{ref}] profile org_relations「{relation_id}」"
    violations.extend(f"{prefix}的 {error}" for error in _org_relation_errors(relation))


def _check_v2_entry(ref, section, entry, tailored, violations):
    bullet_idx = _bullet_index(entry)
    valid_intro_sources = set(bullet_idx) | {ref}

    intro = (tailored.get("intro") or "").strip()
    intro_sources = tailored.get("intro_source_ids") or []
    if intro:
        if not intro_sources:
            violations.append(f"[{ref}] intro 非空但缺少 intro_source_ids")
        for source_id in intro_sources:
            if source_id not in valid_intro_sources:
                violations.append(
                    f"[{ref}] intro_source_ids 引用了同条目中不存在的来源「{source_id}」")
        if intro_sources and all(source_id in valid_intro_sources for source_id in intro_sources):
            _check_new_numbers(
                ref, "intro", intro, _source_text(entry, bullet_idx, intro_sources), violations)

    for bullet_id in tailored.get("bullet_ids", []) or []:
        if bullet_id not in bullet_idx:
            violations.append(f"[{ref}] bullet_ids 引用了同条目中不存在的 bullet「{bullet_id}」")

    overrides = tailored.get("bullet_overrides") or {}
    audits = tailored.get("override_audit") or {}
    for bullet_id, override_text in overrides.items():
        audit = audits.get(bullet_id)
        if not isinstance(audit, dict):
            violations.append(
                f"[{ref}] bullet_overrides「{bullet_id}」缺少匹配的 override_audit")
            continue
        source_ids = audit.get("source_ids") or []
        if not source_ids:
            violations.append(f"[{ref}] override_audit「{bullet_id}」缺少 source_ids")
        invalid_sources = [source_id for source_id in source_ids if source_id not in bullet_idx]
        for source_id in invalid_sources:
            violations.append(
                f"[{ref}] override_audit「{bullet_id}」引用了同条目中不存在的 bullet「{source_id}」")
        change_type = audit.get("change_type")
        if change_type not in ALLOWED_CHANGE_TYPES:
            violations.append(
                f"[{ref}] override_audit「{bullet_id}」的 change_type「{change_type}」非法")
        if not (audit.get("claim_notes") or "").strip():
            violations.append(f"[{ref}] override_audit「{bullet_id}」缺少 claim_notes")
        if source_ids and not invalid_sources:
            _check_new_numbers(
                ref, f"bullet_overrides「{bullet_id}」", override_text,
                _source_text(entry, bullet_idx, source_ids), violations)

    if tailored.get("org_note") is not None:
        violations.append(
            f"[{ref}] v2 禁止内联 org_note；请先把关系写入 profile.org_relations，"
            "tailor 仅填写 org_note_ref")

    org_relation = None
    org_note_ref = tailored.get("org_note_ref")
    if org_note_ref:
        org_relation = _org_relation_index(entry).get(org_note_ref)
        if org_relation is None:
            violations.append(
                f"[{ref}] org_note_ref「{org_note_ref}」未在当前条目 profile.org_relations 中找到")
        else:
            _check_org_relation(ref, org_relation, violations)
            note_display = _org_note_display(org_relation)
            if note_display not in strip_latex(tailored.get("heading", "")):
                violations.append(
                    f"[{ref}] org_note_ref 固定文案「{note_display}」未出现在 heading")

    if section == "experience":
        residual = _heading_residual(entry, tailored, org_relation)
        if residual:
            violations.append(
                f"[{ref}] heading 含未声明附加信息「{residual}」；"
                "请先写入 profile.org_relations，再用 org_note_ref 引用")


def check(profile, tailor):
    """返回违规字符串列表(空 = 全部保真)。"""
    violations = []
    idx = _index(profile)

    schema_v2 = tailor.get("schema_version", 1) >= 2
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

            if schema_v2:
                _check_v2_entry(ref, section, entry, e, violations)

    return violations


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description="保真检查: 关键字段 verbatim + v2 来源审计")
    parser.add_argument("profile", help="master-profile.yaml")
    parser.add_argument("tailor", help="tailor.json")
    args = parser.parse_args(argv)

    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _deps import load_yaml

    try:
        profile = load_yaml(args.profile)
        tailor = _load_json(args.tailor)
    except ImportError:
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
    print("✅ 保真检查通过：关键字段一致；v2 简介/改写/公司旁注来源审计通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
