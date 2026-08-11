# JD 解析与匹配分析

本文件指导编排层（SKILL.md）如何把一份 JD 解析为结构化要求，并产出匹配报告。

## 1. 解析 JD 为结构化要求

无论 JD 来自文本 / URL / 截图，先归一为纯文本，再由 LLM 解析为：

```yaml
jd:
  title: 岗位名称
  mission: "一句话岗位使命：这个岗位要为谁解决什么核心问题"
  top_requirements:       # 只保留决定录用的 Top 3 核心要求，按优先级排序
    - requirement: "能独立开发并迭代 Agent 工作流"
      evidence_refs: [exp-001-b1, proj-002-b2]
      status: covered     # covered / partial / gap
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

### 先定岗位主线，再看关键词

解析结果必须先写出**一句话岗位使命**，说明这个岗位最终要交付什么价值；再从职责、硬性要求和加分项中合并出决定录用的 **Top 3 核心要求**。不要把 JD 的每个词都当作同等重要的要求，也不要用技术名出现次数代替优先级判断。

每个 Top 3 要求都必须同时记录：

- 对应的 profile **证据** id；
- `covered / partial / gap` 状态；
- 若为 `partial` 或 `gap`，缺的到底是能力事实、个人 ownership，还是结果证据。

Top 3 是简历选材、排序和篇幅分配的主线；其余 JD 词只用于次级筛选和 ATS 核对。

### 目标公司实体消歧

当 JD 指向具体公司时，在匹配前先比较目标公司与 profile 中当前/过往雇主：

1. 归一常见中英文名、产品名、公司别名与简称。
2. 只用用户已确认的信息或公司官网、工商主体等权威来源核对关联品牌、集团与法定主体关系。
3. 若目标公司与某段经历可能属于同一主体或品牌体系，主动询问用户用途：回归测试、内部转岗、重复投递，还是确需规避“已在本公司却再次投递”的歧义。
4. 用户确认是测试时保留经历继续；未确认前不擅自删除经历，也不把推断写进 profile。

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
2. **岗位主线**：一句话岗位使命 + Top 3 核心要求，逐项列出证据、状态和缺口。
3. **覆盖表**：其余要求 → 状态（覆盖/部分/缺口）→ 证据 id（来自 profile）。
4. **ATS 关键词命中表**：来自 `ats_check.py`，关键词 → ✅/❌。
5. **缺口清单**：未覆盖的要求，附"是否要补充？"的提问。
6. **补强审计**（见 tailoring-rules.md）：哪些被强调/重排/润色，确保透明、可追溯。

报告的目的：让用户清楚看到"这份简历覆盖了 JD 的哪些点、还差什么、做了哪些真实范围内的强调"。
