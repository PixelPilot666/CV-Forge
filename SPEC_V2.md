# SPEC — CV-Forge 面试官视角优化

> 状态：已实施。

## Objective

在不重做现有架构的前提下，提高按 JD 生成简历的岗位定位、可信度和扫读效率，并修复评审状态与最终交付不一致的问题。

面向中文校招/实习简历，继续使用现有 profile、LaTeX 模板、双评审和有界打磨循环。

## Decisions

- 保留现有 master profile schema，不做 v2 数据迁移。
- 保留 `tailor.json → LaTeX → PDF` 构建链路。
- 保留 reviewer + critic 两个独立评审角色和最多一轮修订。
- ATS 继续生成命中报告，但不再作为简历质量评分维度。
- 一页仍是硬要求；填充率只用于提示拥挤或稀疏，不驱动添加低价值内容。
- 不加入“当前公司与目标公司相同”的检测，本次通用 Agent 场景是测试用例。

## Changes

### 1. 先确定岗位主线，再选择内容

JD 分析先产出：

1. 一句话岗位使命；
2. 三项核心招聘要求；
3. 每项要求对应的真实 profile 证据；
4. 无证据的真实缺口。

生成简历时，前三项要求优先获得版面；不再围绕 ATS 关键词列表组织内容。

### 2. Bullet 从“技术清单”改为“面试证据”

核心 bullet 优先包含：

```text
本人动作 + 关键技术判断/实现 + 结果或可验证产物
```

规则：

- 技术组件罗列不能单独构成高质量 bullet。
- 不要求每条都带数字；没有可靠数字时，清晰的工程约束或故障处理更可信。
- 精确指标必须能解释定义、baseline 和评测方式；否则触发追问，无法补充就弱化或删除。
- 核心实习默认 3–4 条，次要实习 2–3 条，个人项目约 2 条。
- 教育奖项压缩；CVPR 等强信号保留但简洁展示；减少重复技术栈。

### 3. 调整评审标准

仍使用满分 30 的结构，以兼容现有 `polish_gate.py`，但六个维度改为：

| 维度 | 关注点 |
|---|---|
| 岗位主线 | 是否围绕 JD 真正招聘任务，而非关键词堆砌 |
| 证据强度 | 是否有具体经历支撑结论 |
| Ownership | 是否说清本人负责范围和贡献 |
| 可信度 | 指标、术语和项目成熟度是否经得起追问 |
| 影响力 | 是否体现结果、质量、效率或可靠性 |
| 清晰度 | 是否容易扫读、没有长句和组件清单 |

ATS 命中和页面度量继续单独输出，不参与以上总分。Critic 增加三类重点检查：指标定义不明、把顺序工作流包装成 Multi-Agent、技术名词多但缺少决策与结果。

### 4. 修复最终交付一致性

- 修订后的 PDF 必须重新生成 reviewer/critic，再调用 gate；不得复用上一版评审。
- `polish_gate.py` 的最终 state/stdout 是交付状态唯一来源。
- 只有终止态且 `deliverable=true` 才生成 `resume.pdf`；否则生成 `resume.DRAFT.pdf`。
- 报告直接记录 gate 的 decision、score、high flags 和 delivery reason，不自行计算或写不等式。
- 新增回归测试覆盖当前缺陷：23 分、1 个 high flag、state 仍为 revise 时，绝不能输出正式版。

### 5. 页面策略

- 目标页数仍为 1 页；超过一页必须压缩。
- 填充率过高只提示删减，过低只提示素材偏少。
- 不因为页面偏空自动增加兴趣、个人特点、普通奖项或重复 bullet。
- 最终是否可投递主要由一页、无裁切、真实性和评审结论决定，而不是是否铺满 90% 以上。

## Commands

沿用现有命令：

```bash
python3 scripts/validate_profile.py ~/.cv-forge/master-profile.yaml
python3 scripts/check_fidelity.py ~/.cv-forge/master-profile.yaml <out>/tailor.json
python3 scripts/page_metrics.py <out>/resume.pdf
python3 scripts/polish_gate.py --state <out>/polish-state.json \
  --metrics <out>/page_metrics.json --review <out>/reviewer.json \
  --critic <out>/critic.json --target-pages 1
python3 scripts/finalize_delivery.py --state <out>/polish-state.json \
  --pdf <out>/resume.pdf --out-dir <out>
python3 -m unittest discover -s tests -v
```

新增一个小型 `finalize_delivery.py`：只读取终止 state、生成正式版/DRAFT 文件名并输出机器状态摘要，不引入新的框架或依赖。

## Project Structure

预计只改动以下区域：

```text
references/   JD 分析、写作规则、访谈和评审标准
scripts/      现有 gate 的小幅调整；必要时增加最终交付脚本
tests/        评审契约、gate 和端到端回归测试
SKILL.md      调整生成、复审与交付编排
```

## Code Style

沿用项目现有 Python/shell 风格：stdlib 优先、纯函数决策、JSON 输出、`unittest`、无新第三方依赖。确定性判断留在脚本，岗位分析和语言判断留在 agent 指令。

## Testing Strategy

- 文档契约测试：岗位主线、六个新维度、指标可信度规则存在。
- Gate 单测：一页不再因偏空自动判失败；high flag 和低分仍按现有安全规则处理。
- 交付回归：`decision=revise`、`deliverable=false` 或 high flag 均不能生成正式文件名。
- 端到端：修订版必须使用新 reviewer/critic；报告字段与最终 state 一致。
- 手工检查：用通用 Agent fixture 生成一份 PDF，确认主线、密度和追问风险明显改善。

## Boundaries

### Always

- 保留真实性和 verbatim 检查。
- 用脱敏 fixture 做测试。
- 最终修订版重新评审。

### Ask first

- 修改真实 profile。
- 删除已有简历产物。
- 新增第三方依赖。

### Never

- 为 ATS 或填页编造技能、指标和经历。
- 用旧评审结论交付新 PDF。
- 在 state 未终止时输出正式简历。

## Success Criteria

- 通用 Agent 测试中，岗位主线是 Agent 工作流/开发者工具，RAG 是强相关证据但不是全部岗位定义。
- 未定义的 `Top1 81.34%` 被评审要求解释或删除。
- 简历减少技术组件清单，增加 ownership、取舍和可验证结果。
- 修订后 reviewer/critic 的时间和内容对应最终 PDF。
- 不再出现“23 ≥ 24”、`state=revise` 却报告可投递、high flag 遗留却输出正式版。
- 全套测试通过，现有 profile 和构建方式保持兼容。

## Open Questions

无。按以上范围实施，不扩展成新的工作流平台。
