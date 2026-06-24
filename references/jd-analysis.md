# JD 解析与匹配分析

本文件指导编排层（SKILL.md）如何把一份 JD 解析为结构化要求，并产出匹配报告。

## 1. 解析 JD 为结构化要求

无论 JD 来自文本 / URL / 截图，先归一为纯文本，再由 LLM 解析为：

```yaml
jd:
  title: 岗位名称
  hard_requirements:      # 硬性要求(必须满足)
    - "3 年以上后端开发经验"
    - "精通 Python"
  nice_to_have:           # 加分项
    - "有 RAG / 大模型应用经验"
  responsibilities:       # 工作职责
    - "设计并实现高并发服务"
  ats_keywords:           # 用于 ATS 命中核对的关键词(技能/工具/术语)
    - Python
    - FastAPI
    - RAG
  lang: zh                # JD 语言
```

## 2. 逐项匹配（对照 master profile）

把每条要求 / 关键词与 profile 的 `skills` / `tags` / `metrics` / 经历内容比对，分为三类：

| 状态 | 含义 | 处理 |
|---|---|---|
| **覆盖 (covered)** | profile 有明确证据 | 可纳入并按 JD 突出（见 tailoring-rules.md 的"补强"） |
| **部分 (partial)** | 有相关但不完全对应的证据 | 纳入并如实表述（不夸大） |
| **缺口 (gap)** | profile 无任何证据 | **不写入简历**；列入报告，或反问用户是否真的具备 |

> 关键约束：**缺口绝不靠编造填补**（见 `tailoring-rules.md`）。

## 3. ATS 关键词命中核对

用 `scripts/ats_check.py` 对**渲染后的简历纯文本**（PDF 抽取）做关键词命中检查 —— 这才是 ATS 实际读到的内容。脚本输出命中表（关键词 → ✅/❌）。

```bash
python3 "$SKILL/scripts/ats_check.py" jd.txt "$OUT/resume.pdf"
# 或显式给关键词：
python3 "$SKILL/scripts/ats_check.py" --keywords "Python,RAG,FastAPI" "$OUT/resume.pdf"
```

## 4. 匹配报告（match-report.md）结构

生成的 `match-report.md` 应包含：

1. **岗位概览**：标题、JD 语言、解析出的硬性要求/加分项数量。
2. **覆盖表**：每条要求 → 状态（覆盖/部分/缺口）→ 证据 id（来自 profile）。
3. **ATS 关键词命中表**：来自 `ats_check.py`，关键词 → ✅/❌。
4. **缺口清单**：未覆盖的要求，附"是否要补充？"的提问。
5. **补强审计**（见 tailoring-rules.md）：哪些被强调/重排/润色，确保透明、可追溯。

报告的目的：让用户清楚看到"这份简历覆盖了 JD 的哪些点、还差什么、做了哪些真实范围内的强调"。
