<div align="center">

# 📄 jd-resume

**一个开源的 Claude Code Skill — 根据职位描述（JD）自动生成定制化、真实、排版精美的简历。**

以"资深简历专家"的标准打磨内容，守住一条底线：**真实为主，合理补强，绝不编造**。

<p>
<img alt="license" src="https://img.shields.io/badge/license-MIT-blue.svg">
<img alt="python" src="https://img.shields.io/badge/python-3.9%2B-blue.svg">
<img alt="engine" src="https://img.shields.io/badge/PDF-XeLaTeX%20(tectonic)-success.svg">
<img alt="lang" src="https://img.shields.io/badge/简历语言-中文%20(v1)-orange.svg">
</p>

</div>

---

## ✨ 这是什么

把"对着 JD 改简历"这件重复又耗神的事交给 Claude。你只需维护一份个人素材库，
之后每投一个岗位，skill 会按 JD 自动筛选、重排、专业化改写，并编译出一份 PDF + 一份匹配分析报告。

```
JD（文本 / 链接 / 截图）
        │
        ▼
  解析 JD，提取要求与关键词
        │
        ▼
  加载素材库 master-profile.yaml ──► 缺数字？主动向你追问（绝不编造）
        │
        ▼
  匹配分析（覆盖 / 部分 / 缺口 + ATS 关键词命中）
        │
        ▼
  专家裁剪（STAR · 强动词 · 量化 · 专业语言 · 适度加粗）
        │
        ▼
  填模板 → 保真校验 → 编译 PDF → 整页校准
        │
        ▼
  独立子 agent 评审（评审员 + 对抗挑错员，不自评）
        │
        ▼
  resume.pdf  +  match-report.md
```

## 🎯 核心理念

| 理念 | 含义 |
|---|---|
| **真实为主，合理补强** | 只重排、筛选、按 JD 润色、突出已有真实指标；**绝不**编造经历/数字/技能。每次生成都带审计追踪。 |
| **关键信息原样保留** | 姓名、公司名、岗位名、起止时间、论文名、项目名一字不差，由 `check_fidelity.py` 机器校验。 |
| **素材库是长期资产** | 简历是一次性产物；结构化的 `master-profile.yaml` 才是反复复用、越用越完整的核心。 |
| **质量由独立子 agent 评判** | 生成的 agent 不给自己打分（会偏高）；由独立子 agent 打分 + 对抗挑错，不达标自动迭代。 |
| **不绑死运行环境** | LaTeX 引擎运行时探测，缺失则引导安装；降级是你的选择，不是默认。 |

## 🧩 能力一览

- ✅ **JD 多形态输入**：粘贴文本 / 招聘网页链接 / 截图。
- ✅ **专家级写作**：STAR 项目描述、强动词、量化纪律、去 AI 味、适度加粗关键指标。
- ✅ **智能排序**：按 JD 相关性决定章节顺序（如科研 vs 项目谁在前），块内按时间倒序。
- ✅ **整页纪律**：自动校准到接近整页，不足补一类内容、超出则压缩。
- ✅ **ATS 关键词命中检查**：对渲染后 PDF 文本做核对，反映 ATS 真正看到的内容。
- ✅ **保真校验**：关键字段与素材库逐一比对，杜绝改写公司名/论文名等。
- ✅ **独立评审 + 对抗挑错**：双子 agent 评审，揪出虚报、夸大、不专业、不可追溯。
- ✅ **完整审计**：`tailor.json` 记录每条内容来源，`match-report.md` 给出评分与改进清单。

## 📦 功能支持矩阵

| 维度 | v1（当前） | 规划中 |
|---|---|---|
| 简历语言 | 中文 | 英文 / 中英双语 |
| 输出格式 | LaTeX → PDF | 飞书在线文档 / Word(.docx) / Markdown / HTML |
| 模板 | 内置中文经典模板 `zh-classic` | 用户自定义模板 / 联网搜索模板 |
| 素材来源 | 旧简历抽取 + 文档/对话补充 | 项目源码/文档批量抽取 |

---

## 🚀 安装

### 1. 获取 skill

```bash
git clone <this-repo-url> jd-resume
```
把 `jd-resume/` 放到 Claude Code 能加载 skill 的位置（如 `~/.claude/skills/`），或直接在该目录中向 Claude 发起对话。

### 2. 安装 LaTeX 引擎（v1 必需，用于编译中文 PDF）

推荐 [**tectonic**](https://tectonic-typesetting.github.io/)：单二进制、按需下载宏包、跨平台。

```bash
# macOS
brew install tectonic
# Debian / Ubuntu
apt install texlive-xetex          # 或下载 tectonic release
# Windows
winget install tectonic            # 或 scoop install tectonic
```

> 也支持 TeX Live 自带的 `xelatex`。skill 运行时会自动探测引擎，缺失时给出对应系统的安装命令——**不会在缺引擎时静默降级**。

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt    # 仅一个依赖：PyYAML
```

---

## 📖 使用

### 你需要准备什么

1. **一份目标 JD**（文本、网页链接或截图均可）。
2. **你的个人素材**：一份旧简历（`.tex` / `.pdf` / `.md` / `.docx`）或一份项目文档即可起步——skill 会帮你抽取成结构化素材库。

### 步骤

**① 启动**——把目录作为 skill 加载后，对 Claude 说：

> 帮我根据这份 JD 生成简历：
> （粘贴 JD 文本 / 给招聘链接 / 贴截图）

**② 建立素材库（首次）**——skill 会从你的旧简历/文档抽取出 `data/master-profile.yaml`，并就缺失项（如量化指标）**向你追问**。确认补充后即成为你的可复用素材库。

**③ 生成与评审**——skill 自动完成：匹配分析 → 专家裁剪 → 编译 PDF → 保真校验 → 独立子 agent 评审。不达标会自动迭代一轮，并把评审结论写进报告。

**④ 取件**——产物在 `output/<公司>-<岗位>-<语言>-<日期>/`：

| 文件 | 内容 |
|---|---|
| `resume.pdf` | 最终简历（可直接投递） |
| `resume.tex` | LaTeX 源文件（可手动微调） |
| `tailor.json` | 裁剪方案（每条内容的来源审计） |
| `match-report.md` | JD 匹配报告 + ATS 命中 + 独立评审打分与改进清单 |

> 之后换岗位投递，直接复用 `master-profile.yaml`，无需重新录入。

---

## 🗂 项目结构

```
jd-resume/
├── SKILL.md                  # skill 入口：触发条件 + 工作流编排
├── SPEC.md                   # 规格说明
├── references/               # 按需加载的专家知识库
│   ├── resume-craft.md       # 写作准则（STAR/量化/专业语言/整页纪律/技术栈规范…）
│   ├── tailoring-rules.md    # 真实性硬边界（允许补强 vs 禁止编造）
│   ├── profile-schema.md     # 素材库格式定义
│   ├── jd-analysis.md        # JD 解析与匹配分析
│   ├── review-rubric.md      # 六维度评分标准
│   ├── review-agent.md       # 独立子 agent 评审（评审员 + 对抗挑错员）
│   ├── interview.md          # 缺口追问访谈流程
│   └── workflow.md           # 完整工作流展开
├── scripts/                  # 确定性脚本（Python 为主 + 少量 shell）
│   ├── extract_profile.py    # 从 LaTeX 简历抽取素材库
│   ├── validate_profile.py   # 素材库 schema 校验
│   ├── fill_template.py      # 占位符填充 + LaTeX 转义 + 加粗
│   ├── check_fidelity.py     # 关键信息 verbatim 保真校验
│   ├── detect_engine.sh      # 探测 LaTeX 引擎
│   ├── render_pdf.sh         # 编译 PDF（缺引擎给安装指引）
│   └── ats_check.py          # ATS 关键词命中检查
├── assets/templates/zh-classic/   # 内置中文模板（含字体，开箱即用）
├── examples/                 # 脱敏示例（素材库 / JD / 裁剪方案）
├── tests/                    # 单元 + 端到端测试（stdlib unittest）
└── requirements.txt          # PyYAML
```

---

## 🔒 隐私

- 你的真实素材库 `data/master-profile.yaml`（含姓名/电话/邮箱等）与生成产物 `output/` **默认在 `.gitignore` 中**，不会进入版本库。
- 仓库内 `examples/` 仅提供**完全脱敏**的虚构样例。
- 简历照片等本地资源不会被提交。

## 🧪 开发与测试

```bash
python3 -m unittest discover -s tests -v
```
测试基于标准库 `unittest`，无需额外安装。详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 🤝 贡献

欢迎 PR：新增简历模板、扩展语言/输出格式、完善写作准则。请阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)，并确保新模板字体许可证与 MIT 兼容、附测试。

## 📜 许可证

[MIT](./LICENSE)
