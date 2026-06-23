#!/usr/bin/env python3
"""校验 master-profile 是否符合 schema。

用法:
    python3 scripts/validate_profile.py data/master-profile.yaml

退出码: 0 = 通过(可能有软提醒); 非 0 = 有硬性错误。
schema 定义见 references/profile-schema.md。
"""
import argparse
import sys

# 经历类 section -> 每个条目必填的定位字段
# (title 对 experience 推荐但不强制: 抽取/手填时常与 org 合在一行)
SECTION_REQUIRED_FIELDS = {
    "experience": ["org", "date"],
    "projects": ["name"],
    "research": ["name"],
    "education": ["school", "date"],
}
ENTRY_SECTIONS = list(SECTION_REQUIRED_FIELDS.keys())


def validate(profile):
    """返回 (errors, warnings) 两个字符串列表。errors 非空即校验失败。"""
    errors = []
    warnings = []

    if not isinstance(profile, dict):
        return (["素材库根节点必须是映射(dict)"], warnings)

    # --- basics (硬性) ---
    basics = profile.get("basics")
    if not isinstance(basics, dict):
        errors.append("缺少必填的 basics 段")
    else:
        for f in ("name", "phone", "email"):
            val = basics.get(f)
            if not (isinstance(val, str) and val.strip()) and not (
                isinstance(val, (int, float))
            ):
                errors.append(f"basics.{f} 不能为空")

    # --- 经历类 sections: 列表 + 条目 id + 必填字段 ---
    all_entry_ids = []
    all_bullet_ids = []
    for section in ENTRY_SECTIONS:
        if section not in profile:
            continue
        items = profile[section]
        if not isinstance(items, list):
            errors.append(f"{section} 必须是列表")
            continue
        for idx, entry in enumerate(items):
            if not isinstance(entry, dict):
                errors.append(f"{section}[{idx}] 必须是映射(dict)")
                continue
            eid = entry.get("id")
            if not (isinstance(eid, str) and eid.strip()):
                errors.append(f"{section}[{idx}] 缺少非空 id")
            else:
                all_entry_ids.append(eid)
            for req in SECTION_REQUIRED_FIELDS[section]:
                val = entry.get(req)
                if not (isinstance(val, str) and val.strip()):
                    errors.append(
                        f"{section}[{idx}] (id={entry.get('id', '?')}) 缺少必填字段 {req}"
                    )
            for bidx, bullet in enumerate(entry.get("bullets", []) or []):
                if not isinstance(bullet, dict):
                    errors.append(f"{section}[{idx}].bullets[{bidx}] 必须是映射(dict)")
                    continue
                bid = bullet.get("id")
                if not (isinstance(bid, str) and bid.strip()):
                    errors.append(
                        f"{section}[{idx}].bullets[{bidx}] 缺少非空 id"
                    )
                else:
                    all_bullet_ids.append(bid)
                if not (isinstance(bullet.get("text"), str) and bullet["text"].strip()):
                    errors.append(
                        f"{section}[{idx}].bullets[{bidx}] (id={bullet.get('id', '?')}) text 不能为空"
                    )

    # --- id 全局唯一(条目与 bullet 各自空间, 但合并检查避免交叉混淆) ---
    _check_unique(all_entry_ids, "条目 id", errors)
    _check_unique(all_bullet_ids, "bullet id", errors)
    known_ids = set(all_entry_ids) | set(all_bullet_ids)

    # --- skills (软提醒) ---
    skills = profile.get("skills")
    if not skills:
        warnings.append("未填写 skills，建议补充以提升 JD 匹配质量")
    else:
        for group in skills if isinstance(skills, list) else []:
            for item in (group or {}).get("items", []) or []:
                name = item.get("name", "?")
                refs = item.get("evidence_refs") or []
                if not refs:
                    warnings.append(
                        f"技能「{name}」未关联证据(evidence_refs)，请确认属实"
                    )
                for r in refs:
                    if r not in known_ids:
                        warnings.append(
                            f"技能「{name}」的 evidence_refs 指向不存在的 id「{r}」(悬空引用)"
                        )

    if not profile.get("summary"):
        warnings.append("未填写 summary，建议补充自我总结以便按 JD 改写")

    return (errors, warnings)


def _check_unique(ids, label, errors):
    seen = set()
    for i in ids:
        if i in seen:
            errors.append(f"{label}「{i}」重复，必须唯一")
        seen.add(i)


def _load(path):
    import yaml  # 延迟导入，便于在缺依赖时给清晰提示

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验 master-profile schema")
    parser.add_argument("profile", help="master-profile.yaml 路径")
    args = parser.parse_args(argv)

    try:
        profile = _load(args.profile)
    except ImportError:
        print("错误: 需要 PyYAML，请先 pip install -r requirements.txt", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"错误: 找不到文件 {args.profile}", file=sys.stderr)
        return 2

    errors, warnings = validate(profile)

    for w in warnings:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}", file=sys.stderr)

    if errors:
        print(f"\n校验失败: {len(errors)} 个错误, {len(warnings)} 个提醒", file=sys.stderr)
        return 1
    print(f"\n✅ 校验通过 ({len(warnings)} 个软提醒)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
