<div align="center">

# jd-resume

> *「同一份经历，每个岗位都该看到不一样的你。」*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Standard-green)](https://agentskills.io)
[![Runtime](https://img.shields.io/badge/Runtime-Claude%20Code%20·%20Codex%20·%20Cursor-blueviolet)](#安装)
[![PDF](https://img.shields.io/badge/输出-精排%20PDF-success)](#)

<br>

**把一份职位描述丢给它，它按这个岗位把你的简历重写一遍——真实、专业、一页排版精美的 PDF。**

<sub>不是帮你瞎编经历的 AI。是一个懂行的简历专家：只用你真实做过的事，按岗位重新讲一遍。</sub>

[看效果](#效果示例) · [安装](#安装) · [怎么用](#怎么用) · [它凭什么不一样](#它凭什么不一样)

</div>

---

## 效果示例

**同一段实习，投不同的岗位，它讲的故事不一样。**

你素材库里的原始记录：

```
- 做了个推荐系统，用了 RAG、向量召回、BGE-M3 微调，P@1 85→95%
```

投「推荐算法」岗，它强调召回排序与指标：

```
❯ 设计「语义向量召回 + 用户画像排序」双通道，基于 BGE-M3、FAISS 与 RRF 实现混合召回，
  召回精度 P@1 由 85% 提升至 95%，并建立可量化的离线评测体系
```

投「Agent 开发」岗，同一段经历换个重心：

```
❯ 负责检索内核，实现「多子问题扩展 → 双轨检索 → 融合 → Rerank → 引文组装」的多阶段流水线，
  把异构文档变成可检索内容，并产出带引文的回答上下文
```

**它不会替你吹牛。** JD 要 Rust、你没写过，它不会硬塞，而是如实告诉你：

```
❯ 缺口（未写入简历）：Rust —— 你的素材库里没有相关证据。
  如果你确实用过，告诉我在哪用的，我补进去；没有就不写。
```

> 公司名、岗位名、论文名、时间——这些它一个字都不会改，有机器校验兜底。它只重排、筛选、按岗位重新措辞，绝不编造。

---

## 安装

### 一行话搞定（推荐）

打开你在用的 agent（Claude Code / Codex / Cursor 等），对它说：

```
帮我安装这个 skill：https://github.com/<your-name>/jd-resume
```

或用通用安装器：

```bash
npx skills add <your-name>/jd-resume
```

<details>
<summary>手动安装 / 各 runtime 目录</summary>

| Runtime | 路径 |
|---|---|
| Claude Code | `~/.claude/skills/jd-resume/`（或项目内 `.claude/skills/`） |
| Codex CLI | `~/.codex/skills/jd-resume/` |
| Cursor | `~/.cursor/skills/jd-resume/` |
| 其他 | clone 到对应 runtime 的 `skills/` 目录 |

```bash
git clone https://github.com/<your-name>/jd-resume <上面对应的路径>
```

不支持自动加载？直接把 `SKILL.md` 的内容粘进对话也能用——它本质就是一份 markdown。
</details>

**唯一的系统前置**：一个 LaTeX 引擎（编译中文 PDF 用）。装一次：

```bash
brew install tectonic        # macOS
apt install texlive-xetex    # Linux
winget install tectonic      # Windows
```

> Python 依赖全自动，你不用碰 `pip`。没装引擎也不慌——它会停下来告诉你装哪个。

---

## 怎么用

**第一次**，给它一份旧简历或项目文档，它帮你建一份可复用的素材库，并就缺的数字追问你：

```
> 这是我的简历 resume.pdf，帮我建素材库
```

**之后**，投哪个岗位就把 JD 丢给它（文本、链接、截图都行）：

```
> 根据这份 JD 帮我改简历：<粘贴 JD>
> 投字节这个 Agent 岗，简历重点往 Agent 开发上靠
> 这版太满了，压到一页
```

产出在 `output/` 里：可直接投的 `resume.pdf`、能手改的 `resume.tex`、还有一份**匹配报告**——告诉你这份简历覆盖了 JD 哪些要求、ATS 关键词命中多少、哪些是真实缺口。

> 换岗位再投，直接复用素材库，不用重新录入。

---

## 它凭什么不一样

市面上的 AI 简历工具，要么套模板，要么帮你编。这个不。

| | 它怎么做 |
|---|---|
| **真实为主，绝不编造** | 只重排、筛选、按 JD 重新措辞、突出你已有的真实指标。每条内容都能追溯到你的素材，关键信息（公司/岗位/论文/时间）有机器校验，一个字都不许改。 |
| **像专家一样写** | 项目用 STAR 讲清背景与贡献，强动词开头、用数字说话、去掉 AI 腔和空话套话，关键指标加粗。 |
| **一份素材，投十个岗** | 素材库是你的长期资产，越用越全。每次按 JD 现裁，不用一遍遍手改。 |
| **自己不给自己打分** | 生成后交给独立的评审 agent 打分、再来一个专挑刺的找虚报和夸大，不达标自动重改一轮。 |
| **铺满整页，不多不少** | 自动校准到接近整页：不够就补，超了就压，不留半页空白。 |

---

## 许可证

[MIT](./LICENSE) — 随便用，随便改。
