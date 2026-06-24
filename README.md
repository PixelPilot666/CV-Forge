<div align="center">

# CV-Forge

> *「用真实的经历，打磨最契合的简历。」*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Standard-green)](https://agentskills.io)
[![Runtime](https://img.shields.io/badge/Runtime-Claude%20Code%20·%20Cursor%20·%20Codex-blueviolet)](#快速安装)
[![PDF](https://img.shields.io/badge/输出-一页精排%20PDF-success)](#)

<br>

**简历动态重塑引擎。** 丢入岗位 JD，它将提取你的真实素材，自动重写、对齐需求，并生成一页排版的专业 PDF。

[效果演示](#效果演示) · [快速安装](#快速安装) · [使用指南](#使用指南)

</div>

---

## 效果演示

**同一段经历，投递不同岗位时的自适应重写。**

原始素材记录：

```
开发了一套业务监控与分析系统，优化了数据库查询链路，并加入了异常检测模型，
系统响应变快，报警准确率提升了 20%。
```

🎯 投递「算法 / 数据岗」时，聚焦模型与指标：

```
❯ 设计并落地基于时序数据的异常检测算法，构建完善的离线与在线评估体系，
  将核心报警准确率提升 20%，有效降低业务风险。
```

🎯 投递「后端 / 架构岗」时，聚焦工程与性能：

```
❯ 负责监控系统核心链路的架构设计与性能调优，重构底层数据检索与聚合逻辑，
  大幅降低查询延迟，保障系统高并发可用性。
```

### 🛡️ 恪守真实底线

- **拒写幻觉**：若 JD 强要求 Go 语言而你的素材库未提及，系统会抛出「缺口提示」由你确认，**绝不凭空捏造技能**。
- **硬性校验**：公司名、学历、时间节点、论文等客观实体由规则引擎严格兜底，**一字不改**。

---

## 快速安装

将项目克隆至目标 Agent 的 skills 目录即可（Agent 会自动加载 `SKILL.md`）：

| 运行环境 | 安装命令 |
|---|---|
| **Claude Code** | `git clone https://github.com/PixelPilot666/CV-Forge.git ~/.claude/skills/CV-Forge` |
| **Cursor** | `git clone https://github.com/PixelPilot666/CV-Forge.git ~/.cursor/skills/CV-Forge` |
| **Codex CLI** | `git clone https://github.com/PixelPilot666/CV-Forge.git ~/.codex/skills/CV-Forge` |

> **注**：需全局安装一次 LaTeX 引擎以编译中文 PDF：
> ```bash
> brew install tectonic        # macOS
> apt install texlive-xetex    # Linux
> winget install tectonic      # Windows
> ```

---

## 使用指南

### 1. 初始化素材库（仅一次）

将旧简历、项目文档或笔记丢给它，建立可复用的全量事实库。

```
> 这是我的简历 resume.pdf 和开源文档，请提取并建立素材库。
```

### 2. 对齐 JD 生成简历（日常投递）

输入目标职位描述，按需调整侧重点和篇幅。

```
> 根据这份 JD 重写简历：<粘贴 JD>
> 投递后端基础架构岗，简历内容压到一页 PDF，突出工程优化。
```

### 3. 核心产出（`output/`）

- 📄 **`resume.pdf`**：排版就绪、可直接投递的成品简历。
- 📝 **`resume.tex`**：支持像素级二次修改的 LaTeX 源码。
- 📊 **匹配度报告**：展示 JD 覆盖率、ATS 关键词命中情况及真实技能缺口。

---

## 许可证

[MIT](./LICENSE)
