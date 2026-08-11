# Implementation Plan — 面试官视角优化

## Overview

基于现有 CV-Forge 做四项定向改进：岗位主线、证据型写作、面试官评审、交付一致性。保留 profile schema、LaTeX 构建、双评审和有界打磨循环，不引入新的 artifact 系统。

规格：[SPEC_V2.md](../SPEC_V2.md)。

## Dependency Graph

```text
岗位主线与写作规则
        │
        ├── 新评审标准
        │       │
        │       └── 最终复审与交付修复
        │
        └── 页面策略与端到端验收
```

## Task 1: 改写岗位分析和简历写作规则

**Description:** JD 先提炼一句岗位使命和三项核心招聘要求；写作从技术清单转为本人动作、技术判断和结果，并建立简洁内容预算。

**Acceptance criteria:**

- [x] `jd-analysis.md` 明确岗位使命、前三要求、证据和缺口。
- [x] `resume-craft.md` 不再要求每条必须有数字，也不再为填页添加低价值内容。
- [x] `interview.md` 增加 ownership、方案取舍和指标定义追问。

**Verification:** 新增/更新文档契约测试；用通用 Agent JD 人工检查岗位主线。

**Dependencies:** None

**Files likely touched:** `references/jd-analysis.md`, `references/resume-craft.md`, `references/interview.md`, `tests/test_skill_md.py`

**Estimated scope:** M

## Task 2: 用面试官维度替换旧评审维度

**Description:** 保留 reviewer + critic 和 30 分总结构，将六维改为岗位主线、证据、ownership、可信度、影响力、清晰度；ATS 和页面从评分中移除。

**Acceptance criteria:**

- [x] Reviewer JSON 使用六个新维度，仍输出 `total` 供现有 gate 使用。
- [x] Critic 明确检查指标口径、Demo 包装和技术清单化。
- [x] 每条问题仍带 category/severity/axis，兼容 gate 分类。

**Verification:** `python3 -m unittest tests.test_review_agent_schema -v`

**Dependencies:** Task 1

**Files likely touched:** `references/review-rubric.md`, `references/review-agent.md`, `tests/test_review_agent_schema.py`, `tests/fixtures/*.json`

**Estimated scope:** M

## Checkpoint A: 内容与评审

- [x] 通用 Agent fixture 的岗位主线正确。
- [x] `Top1 81.34%` 缺口径时被标记为高风险或 needs-fact。
- [x] 组件清单、ownership 不明和 Demo 包装都能被指出。
- [x] Reviewer/critic schema 与现有 gate 兼容。

## Task 3: 修复最终复审和交付状态

**Description:** 修订版必须重新评审；新增小型 `finalize_delivery.py`，让最终文件名和报告状态只读取终止 gate 结果，避免 agent 手写错误状态。

**Acceptance criteria:**

- [x] Gate 返回 `revise` 后必须生成新 reviewer/critic 才能再次裁决。
- [x] `decision=revise`、`deliverable=false` 或残留 high flag 时不能产生正式 `resume.pdf`。
- [x] 报告记录 gate 原始字段，不再自行写分数不等式。

**Verification:** `python3 -m unittest tests.test_polish_gate tests.test_e2e_polish_loop -v`，新增当前错误场景回归测试。

**Dependencies:** Task 2

**Files likely touched:** `SKILL.md`, `scripts/finalize_delivery.py`, `tests/test_finalize_delivery.py`, `tests/test_e2e_polish_loop.py`

**Estimated scope:** M

## Task 4: 放松填页目标并做端到端验收

**Description:** 一页保留为硬要求，fill ratio 改为稀疏/拥挤提示，不再因偏空添加无关内容；用真实模板验证最终行为。

**Acceptance criteria:**

- [x] 超过一页仍不可交付；单页偏空只给提示。
- [x] 页面偏空不会触发兴趣、普通奖项或重复技术栈填充。
- [x] 通用 Agent 最终 PDF、评审、state 和报告完全一致。

**Verification:** `python3 -m unittest discover -s tests -v`；运行一次通用 Agent 端到端并人工检查 PDF。

**Dependencies:** Tasks 1–3

**Files likely touched:** `SKILL.md`, `scripts/polish_gate.py`, `tests/test_page_metrics.py`, `tests/test_e2e_polish_loop.py`, `SPEC.md`

**Estimated scope:** M

## Checkpoint B: Complete

- [x] 全套测试通过（161 tests）。
- [x] 没有 profile schema、模板体系或输出目录的大改。
- [x] 当前交付矛盾有确定性回归测试。
- [ ] 用户人工确认通用 Agent 样例比当前版本更可信、更容易扫读。

## Risks

| 风险 | 缓解 |
|---|---|
| 新六维评分与旧阈值手感变化 | 保持 30 分总结构，用固定 fixture 校准 24/26 阈值 |
| fill ratio 放松后页面过空 | 作为 warning 写入报告，由用户决定是否补真实内容 |
| Agent 仍可能手写错报告 | 报告状态只复制 gate 字段；用回归测试约束 SKILL 编排 |
| 指标审查过严删掉亮点 | 先追问定义，只有无法解释时才弱化或删除 |

## Verification Commands

```bash
python3 -m unittest tests.test_review_agent_schema -v
python3 -m unittest tests.test_polish_gate tests.test_e2e_polish_loop -v
python3 -m unittest discover -s tests -v
```
