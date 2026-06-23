# 独立评审子 Agent（反自评偏袒）

简历质量评判**必须由独立子 agent 完成**，不能由生成简历的同一个 agent 自评——自评会系统性偏高（看不到自己的盲点、偏袒自己的措辞）。

本流程 spawn **两个独立子 agent**，各自在干净 context 中运行：

1. **评审员（Reviewer）** —— 按 rubric 打分 + 给改进建议。
2. **对抗挑错员（Adversarial Critic）** —— 专门找问题：虚报、夸大、不专业、不可追溯。

主流程（生成 agent）**只负责汇总两者结论并决定是否迭代**，不参与打分。

---

## 共同输入（关键：隔离生成意图）

两个子 agent 的输入**只有**：
- **目标 JD**（或通用岗位画像）原文；
- **渲染后简历的纯文本**（`pdftotext output/<dir>/resume.pdf`）——它们看到的就是 HR / ATS 实际看到的内容；
- 评审标准 `references/review-rubric.md`、`references/resume-craft.md`、真实性边界 `references/tailoring-rules.md`。

**绝不**把 `tailor.json`、master profile、生成思路给评审子 agent——避免"我知道作者想强调什么"污染评分。对抗挑错员可额外拿到 master profile，仅用于核对"是否虚报/超出素材"（见下）。

---

## 子 Agent 一：评审员（Reviewer）

**spawn 指令要点**：

> 你是一位资深简历评审专家，对一份**你未参与撰写**的简历做独立评审。不要假设作者意图、不要替作者找补；你的职责是挑剔而客观地评分。
> 输入：JD + 简历纯文本 + review-rubric.md。
> 按 rubric 六维度（影响力/量化/相关性/清晰度/ATS/页面纪律）各打 1~5 分，给总分（满分 30），并对每个 <5 的维度给出**具体、可执行**的改进点（指明哪句话、怎么改）。
> **反偏袒约束**：默认从严；拿不准就给低分；不得因为"看起来还行"就给高分。

输出 JSON（便于主流程汇总）：
```json
{"scores": {"impact":4,"quantify":3,"relevance":5,"clarity":4,"ats":4,"layout":4},
 "total": 24,
 "improvements": ["proj 段缺真实结果数字……", "..."]}
```

## 子 Agent 二：对抗挑错员（Adversarial Critic）

**spawn 指令要点**：

> 你是一位以"挑刺"为唯一目标的审稿人。假设这份简历**有问题**，你的任务是把问题找出来。重点排查：
> 1. **虚报 / 夸大**：有没有夸大原创性（「提出」实为应用）、夸大规模/指标、声称未必属实的能力？（可对照 master profile 核对，超出素材的一律标红）
> 2. **不专业语言**：泛化动词、形容词自夸、口语、术语不规范（见 resume-craft E2）。
> 3. **技术栈违规**：混入项目名/产品名/荣誉/软技能/语言内置库/纯算法（见 E3）。
> 4. **不可追溯**：有没有 bullet 无法对应到真实经历。
> 找不到问题也要至少报告"已排查项"。宁可误报，不可漏报。

输出 JSON：
```json
{"red_flags": [{"issue":"...", "severity":"high|med|low", "fix":"..."}],
 "checked": ["虚报", "语言", "技术栈", "可追溯"]}
```

---

## 主流程如何使用结论

1. 汇总：综合分 = 评审员 total；对抗挑错员的 **high severity red_flag 视为必须修复项**（无论分数多少）。
2. **交付门槛**：评审 total ≥ 26/30 **且** 无 high severity red_flag。
3. **不达标 → 自动迭代一轮**：
   - 按改进点 + red_flag 修订 tailor.json（仍受真实性边界约束，缺数字只能追问用户、不可编造）；
   - 重新 fill → check_fidelity → render；
   - 再 spawn 一次评审 + 对抗（**最多迭代 1 轮**，避免死循环）。
   - 第 2 轮仍不达标 → 如实把剩余问题写进 match-report，并向用户说明哪些需要补真实信息。
4. 评审与对抗结论、迭代过程，写入 `match-report.md` 的「独立评审」段。

> 实现说明：用所在 harness 的子 agent 能力 spawn（如 Claude Code 的 Agent 工具，agentType 可用通用类型）。若环境无子 agent 能力，**至少**在全新对话/独立调用里完成评审，不要在生成同一上下文里自评。
