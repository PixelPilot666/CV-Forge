<div align="center">

# CV-Forge

> *「每个岗位都该看到最好的你。」*

**把一份职位描述丢给它，它按这个岗位把你的简历重写一遍——真实、专业、一页排版精美的 PDF。**

<sub>用你真实做过的事，按岗位重新讲一遍。</sub>

[效果](#效果示例) · [安装](#安装) · [使用](#怎么用) 

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

### 直接 clone 到你的 agent skills 目录（推荐）

| Runtime | 命令 |
|---|---|
| Claude Code | `git clone https://github.com/PixelPilot666/CV-Forge.git ~/.claude/skills/CV-Forge` |
| Codex CLI | `git clone https://github.com/PixelPilot666/CV-Forge.git ~/.codex/skills/CV-Forge` |
| Cursor | `git clone https://github.com/PixelPilot666/CV-Forge.git ~/.cursor/skills/CV-Forge` |
| 仅在某项目里用 | `git clone https://github.com/PixelPilot666/CV-Forge.git <项目>/.claude/skills/CV-Forge` |

clone 完，agent 会自动发现 `SKILL.md`；不支持自动加载的工具，把 `SKILL.md` 内容粘进对话也能用。

<details>
<summary>用通用安装器（可选）</summary>

[vercel-labs/skills](https://github.com/vercel-labs/skills) 能自动识别当前 runtime 并放到正确目录：

```bash
npx skills add PixelPilot666/CV-Forge
```
</details>

**唯一的系统前置**：一个 LaTeX 引擎（编译中文 PDF 用）。装一次：

```bash
brew install tectonic        # macOS
apt install texlive-xetex    # Linux
winget install tectonic      # Windows
```

---

## 怎么用

**第一次**，给它旧简历、项目文档、源代码等资料，它帮你建一份可复用的素材库。

```
> 这是我的简历 resume.pdf，帮我建素材库
```

**之后**，投哪个岗位就把 JD 丢给它（文本、链接、截图都行）：

```
> 根据这份 JD 帮我改简历：<粘贴 JD>
> 投字节这个 Agent 岗，简历重点往 Agent 开发上靠
> 这版太满了，压到一页
...
```

产出在 `output/` 里：可直接投的 `resume.pdf`、能手改的 `resume.tex`、还有一份**匹配报告**——告诉你这份简历覆盖了 JD 哪些要求、ATS 关键词命中多少、哪些是真实缺口。

> 换岗位再投时，直接复用素材库，不用重新录入。

---

## 许可证

[MIT](./LICENSE) — 随便用，随便改。
