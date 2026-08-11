#!/usr/bin/env python3
"""打磨循环的三态裁决闸门（SPEC §11.5–§11.9 的确定性实现）。

读 page_metrics 输出 + 评审/对抗 JSON + polish-state.json，输出且仅输出三态之一
（pass / revise / deliver-best），并原子回写状态文件。它只做**确定性判定与状态读写**，
不做任何 LLM 判断、不评分、不改写简历内容——"停不停、停在哪一版"由它机器裁决，
取代旧 §5.5/§6 里"直到接近整页且铺满 / 不达标自动迭代"这类不可判定的散文循环。

用法:
    python3 scripts/polish_gate.py --state polish-state.json --metrics page_metrics.json \
        --review reviewer.json --critic critic.json --target-pages 1
退出码: 0 = 终止(看 stdout 的 decision 决定交付哪一版); 10 = 继续迭代(revise);
        2 = 输入缺失/异常(state 或 metrics 读不到 / JSON 非法)。
"""
import argparse
import json
import os
import sys

# ── §11.5 常量（硬上限，机器判定）─────────────────────────────────────────────
MAX_ROUNDS = 1          # 评审迭代至多 1 轮
CAL_MAX = 2             # 单轮内页面校准动作上限
FIDELITY_MAX = 2        # 单轮内保真修复上限
BUILD_RETRY_MAX = 1     # 单轮内编译失败重试上限
DENSITY_WARN_LO = 0.75  # 仅提示内容偏稀疏，不影响裁决
DENSITY_WARN_HI = 0.98  # 仅提示内容偏拥挤，不影响裁决
DELIVER_SCORE = 26      # 达标门槛（评审 total，满分 30）
SOFT_FLOOR = 24         # 软底线：达不到 26 但 ≥24、无 high、且页数正确 → 仍可投递

# 兜底强制分类的关键词（§11.6）——脚本侧消除"按需归类"
NEEDS_FACT_KEYWORDS = ("缺数字", "缺真实数字", "无证据", "缺口", "规模",
                       "缺数据", "缺指标", "缺成果")


def page_count_ok(pages_int, n):
    """页数是交付硬约束：实际页数必须与显式目标 N 相等。"""
    return pages_int == n


def density_warning(fill_ratio):
    """把填充率转为只读提示；它不参与评分、选 best 或交付判定。"""
    if fill_ratio is None:
        return None
    if fill_ratio < DENSITY_WARN_LO:
        return "sparse"
    if fill_ratio > DENSITY_WARN_HI:
        return "dense"
    return None


def _page_ok(candidate, n):
    """Read current page status, with a fallback for pre-change state snapshots."""
    if "page_ok" in candidate:
        return bool(candidate["page_ok"])
    if candidate.get("pages") is not None:
        return page_count_ok(candidate["pages"], n)
    return bool(candidate.get("in_band", False))


def _classify(item, is_red_flag):
    """把一条评审发现归入 actionable / needs-fact（§11.6 兜底强制分类）。

    优先级：① 任意 high red flag → 强制 actionable（先删除/降级当前可疑表述，不引入新事实）；
            ② needs_new_fact==true 或命中缺数字/无证据等关键词 → 强制 needs-fact；
            ③ 否则采用评审子 agent 自报的 category。
    """
    text = item.get("issue" if is_red_flag else "text", "") or ""
    sev = item.get("severity")
    if is_red_flag and sev == "high":
        return "actionable"
    if item.get("needs_new_fact") is True:
        return "needs-fact"
    if any(k in text for k in NEEDS_FACT_KEYWORDS):
        return "needs-fact"
    return item.get("category", "")


def actionable_count(reviewer, critic):
    """统计"无需新事实即可修"的发现条数（只有这类才触发 REVISE）。"""
    count = 0
    for imp in (reviewer or {}).get("improvements", []) or []:
        if _classify(imp, is_red_flag=False) == "actionable":
            count += 1
    for rf in (critic or {}).get("red_flags", []) or []:
        if _classify(rf, is_red_flag=True) == "actionable":
            count += 1
    return count


def _count_severity(critic, level):
    return sum(1 for rf in (critic or {}).get("red_flags", []) or []
               if rf.get("severity") == level)


def dimension_floor_ok(reviewer):
    """Require every supplied hiring-axis score to exceed the rubric floor.

    Older reviewer payloads may not have a scores object; total-only behavior is
    retained for those payloads, while malformed supplied scores fail closed.
    """
    scores = (reviewer or {}).get("scores")
    if not scores:
        return True
    return all(isinstance(value, (int, float)) and not isinstance(value, bool)
               and value > 2 for value in scores.values())


def strictly_better(cand, best, n):
    """§11.7 单调改进偏序：候选是否**严格优于** best（字典序，短路）。

    1) high_flags 更少者优（真实性第一；removing high 可越过整页硬闸）；
    2) page_ok 真者优（页数硬闸，仅 high 减少可豁免——已被第 1 档吸收）；
    3) med_flags 更少者优（red_flag 减少优先于 total，保护已修复版本不被噪声推翻）；
    4) total 高者优；
    5) 前四项相同即并列；fill_ratio 不参与 best 选择。
    """
    # best 为 null，或快照未填充（high_flags 仍是 null）→ 视为最差，任何真实版严格优于它
    if best is None or best.get("high_flags") is None:
        return True
    if cand["high_flags"] != best["high_flags"]:
        return cand["high_flags"] < best["high_flags"]
    cand_page_ok = _page_ok(cand, n)
    best_page_ok = _page_ok(best, n)
    if cand_page_ok != best_page_ok:
        return cand_page_ok and not best_page_ok
    if cand.get("med_flags", 0) != best.get("med_flags", 0):
        return cand.get("med_flags", 0) < best.get("med_flags", 0)
    cs, bs = cand.get("score"), best.get("score")
    if cs is not None and bs is not None and cs != bs:
        return cs > bs
    return False


def _snapshot(cand, prev_best):
    """把候选指标固化成 best 快照，保留上一 best 的文件路径字段。"""
    paths = {"tex_path": "resume.tex", "pdf_path": "resume.pdf",
             "tailor_path": "tailor.json"}
    if prev_best:
        for k in ("tex_path", "pdf_path", "tailor_path"):
            if prev_best.get(k):
                paths[k] = prev_best[k]
    return {"round": cand["round"], "score": cand["score"], "pages": cand["pages"],
            "fill_ratio": cand["fill_ratio"], "pages_float": cand["pages_float"],
            "high_flags": cand["high_flags"], "med_flags": cand["med_flags"],
            "page_ok": cand["page_ok"], **paths}


def _deliver_best_reason(cand, state, n, act, better):
    """为 deliver-best 选一个机器可判定的终止原因枚举（§11.8 / §11.9 汇总表）。"""
    round_ = state.get("round", 0)
    max_rounds = state.get("max_rounds", MAX_ROUNDS)
    cal = state.get("cal", 0)
    max_cal = state.get("max_cal", CAL_MAX)
    if state.get("oscillated", False):
        return "oscillation"
    if cal >= max_cal and not cand["page_ok"]:
        return "calib_exhausted"
    if not cand["page_ok"]:
        return "page_count_mismatch"
    if round_ >= max_rounds and act >= 1:
        return "max_rounds_reached"
    if act == 0:
        return "only_factual_gaps"
    if not better:
        return "no_improvement"
    return "max_rounds_reached"


def decide(state, metrics, reviewer, critic, n):
    """核心三态裁决（§11.8）。返回 (result_dict, new_state)。纯函数，无副作用 I/O。"""
    pages_int = metrics["pages_int"]
    fill_ratio = metrics.get("fill_ratio")
    pages_float = metrics.get("pages_float")
    high = _count_severity(critic, "high")
    med = _count_severity(critic, "med")
    score = (reviewer or {}).get("total")
    page_ok = page_count_ok(pages_int, n)
    axis_floor_ok = dimension_floor_ok(reviewer)

    cand = {"score": score, "high_flags": high, "med_flags": med,
            "fill_ratio": fill_ratio, "pages_float": pages_float,
            "page_ok": page_ok, "pages": pages_int, "round": state.get("round", 0)}

    old_best = state.get("best")
    if old_best is not None and old_best.get("high_flags") is None:
        old_best = None       # 未填充的初始快照视为"无 best"（§11.4）
    act = actionable_count(reviewer, critic)
    better = strictly_better(cand, old_best, n)        # 候选 vs 旧 best（§11.7 算子顺序）
    round_ = state.get("round", 0)
    max_rounds = state.get("max_rounds", MAX_ROUNDS)
    oscillated = state.get("oscillated", False)

    if (high == 0 and score is not None and score >= DELIVER_SCORE
            and page_ok and axis_floor_ok):
        decision, reason = "pass", "pass"
    elif round_ < max_rounds and act >= 1 and better and not oscillated:
        decision, reason = "revise", "needs_revision"
    else:
        decision = "deliver-best"
        reason = _deliver_best_reason(cand, state, n, act, better)

    new_state = dict(state)
    if decision == "revise":
        # 先判 revise（用旧 best），再在 REVISE 入口更新 best 快照（§11.7）
        new_state["best"] = _snapshot(cand, old_best)
        new_state["round"] = round_ + 1
        new_state["cal"] = 0
        deliverable = None
    else:
        if better or old_best is None:
            new_state["best"] = _snapshot(cand, old_best)
        # `best` remains the historical comparison winner, but the only PDF on
        # disk is the candidate just reviewed. `selected` keeps delivery metadata
        # aligned with that materialized file without introducing artifact copies.
        selected = _snapshot(cand, None)
        new_state["selected"] = selected
        deliverable = (selected["high_flags"] == 0 and _page_ok(selected, n)
                       and selected["score"] is not None
                       and selected["score"] >= SOFT_FLOOR)
        new_state["terminated"] = True
        new_state["deliverable"] = deliverable

    new_state["last_pages"] = pages_int
    new_state["last_fill_ratio"] = fill_ratio
    new_state["last_density_warning"] = density_warning(fill_ratio)
    new_state["last_score"] = score
    new_state["last_high_flags"] = high
    # This review describes the candidate at the round value before any REVISE
    # increment. A terminal state is fresh only when this equals state.round.
    new_state["last_review_round"] = cand["round"]
    new_state["has_actionable"] = act >= 1
    new_state["decision"] = decision
    new_state["delivery_reason"] = None if decision == "revise" else reason

    result = {"decision": decision, "reason": reason, "round": new_state.get("round"),
              "total": score, "fill_ratio": fill_ratio,
              "density_warning": density_warning(fill_ratio), "page_ok": page_ok,
              "dimension_floor_ok": axis_floor_ok,
              "high_flags": high,
              "deliverable": deliverable}
    return result, new_state


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="打磨循环三态裁决闸门")
    parser.add_argument("--state", required=True, help="polish-state.json（会被原子改写）")
    parser.add_argument("--metrics", required=True, help="page_metrics.py 输出的 JSON")
    parser.add_argument("--review", required=True, help="评审员 reviewer.json")
    parser.add_argument("--critic", required=True, help="对抗挑错员 critic.json")
    parser.add_argument("--target-pages", type=int, default=1, help="目标页数 N")
    args = parser.parse_args(argv)

    # state / metrics 读不到或非法 → exit 2（输入缺失/异常）
    try:
        state = _load_json(args.state)
        metrics = _load_json(args.metrics)
    except FileNotFoundError as ex:
        print(f"错误: {ex}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as ex:
        print(f"错误: JSON 非法: {ex}", file=sys.stderr)
        return 2

    # review / critic 读不到或非法 → 不是 exit 2，而是 review_unavailable 单向汇入 DELIVER（§11.8）
    try:
        reviewer = _load_json(args.review)
        critic = _load_json(args.critic)
    except (FileNotFoundError, json.JSONDecodeError) as ex:
        print(f"⚠️ 评审输入不可用，按 review_unavailable 交付：{ex}", file=sys.stderr)
        new_state = dict(state)
        new_state["terminated"] = True
        new_state["decision"] = "deliver-best"
        new_state["delivery_reason"] = "review_unavailable"
        new_state["deliverable"] = False
        new_state["last_review_round"] = None
        pages_int = metrics.get("pages_int")
        selected = {
            "round": state.get("round", 0), "score": None,
            "pages": pages_int, "fill_ratio": metrics.get("fill_ratio"),
            "pages_float": metrics.get("pages_float"), "high_flags": None,
            "med_flags": None,
            "page_ok": page_count_ok(pages_int, args.target_pages),
            "tex_path": "resume.tex",
            "pdf_path": "resume.pdf", "tailor_path": "tailor.json"}
        new_state["selected"] = selected
        new_state["last_pages"] = pages_int
        new_state["last_fill_ratio"] = metrics.get("fill_ratio")
        new_state["last_density_warning"] = density_warning(
            metrics.get("fill_ratio"))
        new_state["last_score"] = None
        new_state["last_high_flags"] = None
        new_state["has_actionable"] = None
        if new_state.get("best") is None:
            new_state["best"] = selected
        _atomic_write(args.state, new_state)
        print(json.dumps({"decision": "deliver-best", "reason": "review_unavailable",
                          "round": state.get("round"), "total": None,
                          "fill_ratio": metrics.get("fill_ratio"),
                          "density_warning": density_warning(metrics.get("fill_ratio")),
                          "page_ok": page_count_ok(metrics.get("pages_int"),
                                                   args.target_pages),
                          "dimension_floor_ok": None,
                          "high_flags": None,
                          "deliverable": False}, ensure_ascii=False))
        return 0

    result, new_state = decide(state, metrics, reviewer, critic, args.target_pages)
    _atomic_write(args.state, new_state)
    print(json.dumps(result, ensure_ascii=False))
    return 10 if result["decision"] == "revise" else 0


if __name__ == "__main__":
    sys.exit(main())
