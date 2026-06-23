# jd-resume

> 一个开源的 Claude Code skill：根据职位描述（JD）从你的个人素材库自动生成**定制化、真实、排版精美**的简历，并附 JD 匹配分析报告。

## 这是什么

把简历定制这件重复又耗神的事交给 AI，但守住一条底线：**真实为主，允许合理补强，绝不编造**。

工作流：

```
JD（文本 / URL / 截图）
  → 解析 JD，提取要求与关键词
  → 加载你的素材库 master-profile.yaml
  → 匹配分析（覆盖 / 部分 / 缺口 + ATS 关键词命中）
  → 按 JD 真实裁剪（只重排 / 筛选 / 润色 / 突出真实指标）
  → 填入 LaTeX 模板并编译
  → 输出 resume.pdf + match-report.md
```

## 核心理念

1. **真实为主，合理补强** — 只能重排、筛选、按 JD 词汇润色、突出已有的真实指标；绝不编造经历 / 数字 / 技能。每次生成都带审计追踪（`tailor.json`）。
2. **素材库是长期资产** — 简历是一次性产物，结构化的 `master-profile.yaml` 才是反复复用、越用越完整的核心。
3. **不绑死运行环境** — 外部依赖（LaTeX 引擎）运行时探测，缺失则引导你安装；降级是你的选择，不是默认。

## 功能支持矩阵

| 维度 | v1（当前） | 后续迭代 |
|---|---|---|
| 语言 | 中文 | 英文 / 中英双语 |
| 输出格式 | LaTeX → PDF | 飞书在线文档 / Word(.docx) / Markdown / HTML |
| 模板 | 内置中文经典模板（zh-classic） | 用户自定义模板 / 网络搜索模板 |
| 素材来源 | 从旧简历抽取 + 对话补充 | 从项目源码 / 文档批量抽取 |
| JD 匹配分析 | ✅ 完整（覆盖表 + ATS 命中 + 补强审计） | — |

## 安装与依赖

**1. LaTeX 引擎（v1 必需，用于编译中文 PDF）** — 推荐 [tectonic](https://tectonic-typesetting.github.io/)（单二进制、按需下载宏包、跨平台）：

```bash
# macOS
brew install tectonic
# Debian / Ubuntu
apt install texlive-xetex        # 或下载 tectonic release
# Windows
winget install tectonic          # 或 scoop install tectonic
```

> 也支持 TeX Live 自带的 `xelatex`。skill 会在运行时自动探测，缺失时给出对应系统的安装命令。

**2. Python 依赖**：

```bash
pip install -r requirements.txt   # 仅 PyYAML
```

## 快速开始

把这个目录作为 skill 安装后，对 Claude 说：

> 帮我根据这份 JD 生成简历：<粘贴 JD / 给链接 / 贴截图>

首次运行会从你现有简历抽取出 `data/master-profile.yaml`，请你确认补充；之后每次按 JD 复用裁剪。

## 隐私

`data/master-profile.yaml` 含个人隐私信息（姓名 / 电话 / 邮箱等），已在 `.gitignore` 中默认排除，不会进入版本库。`examples/` 下仅提供脱敏样例。

## 许可证

[MIT](./LICENSE)
