# 独立评审子 Agent（反自评偏袒）

简历质量评判**必须由独立子 agent 完成**，不能由生成简历的同一个 agent 自评——自评会系统性偏高（看不到自己的盲点、偏袒自己的措辞）。

本流程 spawn **两个独立子 agent**，各自在干净 context 中运行：

1. **评审员（Reviewer）** —— 按 rubric 打分 + 给改进建议。
2. **对抗挑错员（Adversarial Critic）** —— 专门找问题：虚报、夸大、不专业、不可追溯。

主流程（生成 agent）**只负责汇总两者结论并决定是否迭代**，不参与打分。

---

## 共同输入（关键：隔离生成意图）

两个子 agent 的输入**只有**：
- 冻结的 `$OUT/target-role.json`（包含目标 JD 或通用岗位画像的使命、Top 3 与 ATS 词）；
- **渲染后简历的纯文本**（`pdftotext $OUT/resume.pdf`）——它们看到的就是 HR / ATS 实际看到的内容；
- 评审标准 `references/review-rubric.md`、`references/resume-craft.md`、真实性边界 `references/tailoring-rules.md`；
- `$OUT/layout-check.json` 与首页预览，用于核对粗体、重叠、截断和留白；先核对其中 `pdf_sha256` 对应当前 PDF，避免沿用上一轮截图。

**绝不**把 `tailor.json`、master profile、生成思路给 Reviewer——避免"我知道作者想强调什么"污染评分。Adversarial Critic 可额外拿到 master profile 与 `tailor.json` 的 `intro_source_ids` / `override_audit` / `org_note_ref`，仅用于核对是否虚报、超出素材或缺证据。

---

## 子 Agent 一：评审员（Reviewer）

**spawn 指令要点**：

> 你是一位资深简历评审专家，对一份**你未参与撰写**的简历做独立评审。不要假设作者意图、不要替作者找补；你的职责是挑剔而客观地评分。
> 输入：target-role.json + 简历纯文本 + review-rubric.md + layout-check.json / 首页预览。
> 按 rubric 六维度（岗位主线/证据强度/个人贡献/可信度/影响力/清晰度）各打 1~5 分，给总分（满分 30），并对每个 <5 的维度给出**具体、可执行**的改进点（指明哪句话、怎么改）。ATS 命中和页面状态另做独立检查，不计入 30 分。
> 对核心 bullet 额外检查是否自然呈现“问题—方法—结果”，但不得要求机械标签或统一句式。
> **反偏袒约束**：默认从严；拿不准就给低分；不得因为"看起来还行"就给高分。

输出 JSON（便于 `polish_gate.py` 机器汇总）。**每条 `improvement` 必须是对象**，自带两个机器字段（见下「分类字段」）：
```json
{"scores": {"role_focus":4,"evidence":4,"ownership":3,"credibility":3,"impact":5,"clarity":5},
 "total": 24,
 "improvements": [
   {"text": "把 Agent 工作流证据置顶，使其直接回应岗位使命", "category": "actionable", "axis": "role_focus"},
   {"text": "Top1 81.34% 缺指标口径、基线和评测方式", "category": "needs-fact", "axis": "credibility", "needs_new_fact": true}
 ],
 "checks": {"ats": "pass", "layout": "one-page; dense warning"}}
```

**分类字段（`category` / `axis`，§11.6 要求）**：
- `category`：`"actionable"`（无需新事实即可在 tailor.json 内修：排序/措辞/加粗/术语/技术栈违规/删冗余）或 `"needs-fact"`（需要真实数据才能修：缺数字、JD 要求是缺口）。**只有 `actionable` 才触发自动迭代**；`needs-fact` 走 `interview.md` 追问或写进缺口段。
- `axis`：命中的维度（`role_focus`/`evidence`/`ownership`/`credibility`/`impact`/`clarity`）。ATS 与 layout 是独立检查结果，不得作为 `axis` 或计入 `scores`。
- 当某条改进需要引入 profile 里没有的新事实时，再加 `"needs_new_fact": true`（`polish_gate.py` 会据此强制归为 `needs-fact`，防"想改就标 actionable"）。

## 子 Agent 二：对抗挑错员（Adversarial Critic）

**spawn 指令要点**：

> 你是一位以"挑刺"为唯一目标的审稿人。假设这份简历**有问题**，你的任务是把问题找出来。重点排查：
> 1. **虚报 / 夸大**：有没有夸大原创性（「提出」实为应用）、夸大规模/指标、声称未必属实的能力？（可对照 master profile 核对，超出素材的一律标红）
> 2. **指标口径**：数字是否说明测了什么；提升是否有基线；离线结果是否有数据集和评测方式。无法解释的精确数字按可信度风险处理。
> 3. **Demo 包装**：是否把个人 Demo、课程项目或原型包装成生产上线；是否用「多 Agent」掩盖普通串行调用，成熟度必须与证据一致。
> 4. **组件清单**：bullet 是否只罗列框架、数据库和模块，却没有本人动作、关键技术选择与结果。
> 5. **个人贡献**：团队成果与候选人 ownership 是否混淆，是否冒领他人模块或整体指标。
> 6. **不专业语言与技术栈违规**：泛化动词、形容词自夸、术语不规范，或技术栈混入项目名/产品名/软技能等。
> 7. **不可追溯**：有没有 bullet 无法对应到真实经历。
> 8. **问题—方法—结果缺失**：核心 bullet 是否只有组件或职责，没有说明要解决的问题、关键方法或实际结果；结果可为确定性能力或风险收敛，不强求数字。
> 9. **约束层级错写**：是否把 Prompt 约束包装成运行时保证，把 LLM 调用上限写成工具调用上限，或省略拒答的会话范围。
> 10. **公司法定主体与关系旁注**：法定主体是否完整保留；集团/品牌关系是否有依据、是否被夸大为直接雇主；同一公司显示单元是否整体加粗且未在简介重复。
> 11. **调参过程喧宾夺主**：融合权重、超参数或网格搜索细节是否挤占结果指标；指标是否说明对象、样本、基线和评测方式。
> 找不到问题也要至少报告"已排查项"。宁可误报，不可漏报。

输出 JSON。**每条 `red_flag` 同样自带 `category`/`axis`**（字段含义同上）：
```json
{"red_flags": [
   {"issue":"将个人 Demo 写成生产级多 Agent 系统，现有证据不支持", "severity":"high",
    "fix":"降级为原型并明确本人实现范围，或删除生产级表述", "category":"actionable", "axis":"credibility",
    "needs_new_fact": false}
 ],
 "checked": ["虚报", "指标口径", "Demo 包装", "组件清单", "个人贡献", "问题—方法—结果", "Prompt 约束", "公司法定主体", "调参过程", "可追溯"]}
```

> **兜底分类（`polish_gate.py` 强制，§11.6）**：凡 `severity=="high"` 的 red flag 一律优先强制 `actionable`（先**删除或降级**当前可疑内容，不引入新事实）；其余发现若 `needs_new_fact==true` 或文案命中"缺数字/无证据/规模/缺口"等，再强制 `needs-fact`。这样 `category` 由脚本据字段计数，**不由生成 agent 事后按需归类**。

**优先级**：当前正文中的 high 虚报/夸大/超出素材项，先按 `actionable` **删除或降级**到现有证据支持的强度；“若未来补到证据可再加入”才另记为 `needs-fact`。只要 high flag 未清零，该版本就**不得进入正式 PDF**，不能因为同时缺事实而暂留正文。

---

## 主流程如何使用结论（裁决权归 SPEC §11）

评审本身只**产出**两份带 `category`/`axis` 字段的 JSON；**"停不停、迭代几轮、交付哪一版"由 `scripts/polish_gate.py` 按 SPEC §11 机器裁决**，不再由本文档的散文循环决定。主流程：

1. 把评审员 / 对抗挑错员的 JSON 落盘（`reviewer.json` / `critic.json`），连同 `page_metrics.py` 的页数+`fill_ratio` 与 `polish-state.json` 一起喂给 `polish_gate.py`。
2. `polish_gate.py` 输出三态之一：`pass` / `revise` / `deliver-best`，并回写状态文件。真实退出码为：**0 = 终止**（再看 `decision` 是 pass 还是 deliver-best）、**10 = revise**、**2 = 输入缺失/异常**。主流程只按退出码分支；修订受 `MAX_ROUNDS=1` 封顶，exit 2 不进入自由重试循环。
3. `actionable` vs `needs-fact` 的处置、`high severity red_flag` 必须删除（P6）、`total≥26`/`SOFT_FLOOR=24` 门槛、keep-best 与必然终止出口——**一律以 SPEC §11.5–§11.11 为准**；本文档与 §11 冲突时以 §11 为准。
4. 评审与对抗结论、迭代过程、`delivery_reason` 写入 `match-report.md` 的「独立评审」段（§11.11）。

> 实现说明：用所在 harness 的子 agent 能力 spawn（如 Claude Code 的 Agent 工具，agentType 可用通用类型）。若环境无子 agent 能力，**至少**在全新对话/独立调用里完成评审，不要在生成同一上下文里自评。评审 spawn 失败/返回非法 JSON 时，`polish_gate.py` 按 `review_unavailable` 单向汇入交付（§11.8），不重试。
