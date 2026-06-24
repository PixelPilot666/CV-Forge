# SPEC — `jd-resume` Skill (v1)

> 一个开源的 Claude Code skill：根据职位描述（JD）从个人素材库生成定制化简历。
> **本文件是 v1 的规格说明（spec-driven development 的设计交付物）。实现以此为准。**

---

## 1. Objective（目标）

**一句话**：给定一份 JD 和用户的素材库（master profile），自动产出一份**真实、贴合该 JD、排版精美**的中文简历 PDF，并附一份 JD 匹配分析报告。

**v1 范围（聚焦验证“做简历”的核心能力）：**
- 语言：**仅中文**。
- 输出：**仅 LaTeX → PDF**，使用用户提供的 xeCJK 中文简历模板（已实测可由 tectonic 零改动编译）。
- 编译引擎：**tectonic**（首选）或 **xelatex**；运行时探测，缺失则**引导用户安装**，不静默降级。
- 素材库：v1 从用户现有简历 `resume.tex` 抽取生成结构化 `master-profile.yaml` 作为起点。
- 闭环：**JD 解析 → 加载素材库 → 匹配分析 → 按 JD 真实裁剪 → 填模板 → 编译 PDF → 输出匹配报告**。

**明确不在 v1 范围（留待后续迭代）：**
- 其他语言（英文/双语）、其他输出格式（飞书 / docx / Markdown / HTML）。
- 用户自定义模板加载、网络搜索模板。
- 从任意项目源码/文档批量抽取素材（v1 仅支持手动补充与从旧简历抽取）。
- HTML/soffice 等 PDF 降级链（v1 只走 LaTeX；引擎缺失时引导安装）。

**设计哲学（贯穿全程，面向广大开源用户）：**
1. **不绑死本机环境**：所有外部能力（LaTeX 引擎等）运行时探测；缺失则按操作系统给出安装指引并停下等待，**降级是用户的选择而非默认**。
2. **真实为主，允许合理补强**：只可重排、筛选、按 JD 词汇润色、突出已有的真实指标；**绝不编造**经历/数字/技能。这是硬边界（见 §6）。
3. **素材库是长期资产**：简历是一次性产物，结构化的 master profile 才是反复复用、越用越完整的核心。

---

## 2. Commands（关键命令 / 脚本接口）

v1 脚本以 **Python 为主 + 少量 shell**，stdlib 优先。

| 命令 | 作用 | 退出约定 |
|---|---|---|
| `bash scripts/detect_engine.sh` | 探测 tectonic/xelatex，输出 JSON：`{"engine":"tectonic","available":true,...}` | 0=找到，非0=未找到 |
| `python3 scripts/extract_profile.py <resume.tex> -o master-profile.yaml` | 从现有 LaTeX 简历抽取结构化素材库 | 0=成功 |
| `python3 scripts/validate_profile.py <profile.yaml>` | 校验素材库是否符合 schema，列出缺失/软提醒项 | 0=通过 |
| `python3 scripts/fill_template.py <profile.yaml> <tailor.json> -o resume.tex` | 将裁剪结果填入模板（含 LaTeX 转义） | 0=成功 |
| `bash scripts/render_pdf.sh <resume.tex> -o <outdir>` | 用探测到的引擎编译 PDF | 0=成功，非0=引擎缺失/编译失败 |
| `python3 scripts/ats_check.py <jd.txt> <resume.pdf>` | JD 关键词 vs 渲染后 PDF 纯文本，输出命中表 | 0=完成 |

> 裁剪（tailor）这一步由 **LLM 判断**完成，不是脚本：agent 读 JD + profile，产出一个 `tailor.json`（选了哪些 id、每条 bullet 的最终文案、章节顺序），再交给 `fill_template.py`。脚本只做确定性的“填充 + 转义 + 编译”。

---

## 3. Project Structure（项目结构）

```
jd-resume/
├── SKILL.md                       # 触发用 frontmatter + 编排说明（简短，渐进式加载）
├── SPEC.md                        # 本文件
├── README.md                      # 简介、安装、快速开始、格式支持矩阵
├── LICENSE                        # MIT
├── CONTRIBUTING.md                # 如何加模板、跑测试、代码风格
├── .gitignore                     # output/、data/master-profile.*（含 PII）、*.pdf 中间产物
├── requirements.txt               # 可选 python 依赖（pyyaml 等）；stdlib 优先
├── references/                    # 按需加载的深度文档
│   ├── profile-schema.md          # master profile schema + 字段说明 + 样例
│   ├── workflow.md                # 完整工作流（状态机展开）
│   ├── jd-analysis.md             # JD 解析、匹配报告、ATS 关键词逻辑
│   ├── tailoring-rules.md         # “真实为主，合理补强” 硬边界规则
│   └── template-guide.md          # 模板命令说明、占位符约定
├── scripts/
│   ├── detect_engine.sh
│   ├── extract_profile.py
│   ├── validate_profile.py
│   ├── fill_template.py
│   ├── render_pdf.sh
│   └── ats_check.py
├── assets/
│   └── templates/
│       └── zh-classic/            # 用户这套 xeCJK 中文模板（v1 内置默认）
│           ├── resume.cls
│           ├── resume.tex.tmpl    # 占位符化后的模板
│           ├── *.sty              # zh_CN-Adobefonts_external、linespacing_fix、fontawesome
│           ├── fonts/             # 内置中/英字体（相对路径，保证可移植）
│           ├── images/            # 占位照片（可选）
│           └── template.json      # 元信息：id, engine=tectonic, lang=zh, ats_safe
├── examples/
│   ├── sample-jd.txt              # 演示 JD
│   └── sample-master-profile.yaml # 从用户简历抽取的样例素材库（脱敏）
├── tests/
│   ├── test_fill_template.py      # 占位符 + LaTeX 转义正确性
│   ├── test_validate_profile.py
│   └── fixtures/
└── data/
    └── master-profile.yaml        # 用户真实素材库（gitignore，含 PII）
```

---

## 4. Master Profile Schema（素材库格式）

YAML，人类可手维护。v1 从用户 `resume.tex` 抽取生成。详见 `references/profile-schema.md`。

**核心约定：**
- **稳定 id**：`experience`/`projects`/`research` 下每个条目和每条 bullet 都有 id。裁剪 = 选择/重排/润色这些 id，**不新增 id**。
- **`evidence_refs`（可选 + 软提醒）**：技能可指向证明它的经历/项目 id。填了 → 匹配报告能给出证据来源；没填 → 不报错，生成时标注“⚠️ 此技能未关联证据，请确认属实”。
- **结构化 `metrics`**：把真实数字（如 P@1 85%→95%）结构化存储，补强 = 复用真实数字，而非编造。
- **`tags`**：与 JD 要求匹配的语义标签。

v1 关键 section（对应模板的四块）：`basics`（姓名/手机/邮箱/照片）、`summary`、`skills`、`education`、`experience`（实习）、`projects`、`research`（科研/论文）、`awards`、`preferences`（target_titles、max_pages、exclude_ids — 不打印，仅指导裁剪）。

---

## 5. End-to-End Workflow（工作流，SKILL.md 编排）

1. **接 JD** — 文本（直接）/ URL（WebFetch）/ 截图·PDF（agent 视觉读取或 pdf 提取）。检测确认为中文。保存原文用于 ATS 关键词提取。
2. **加载/建素材库** — 若 `data/master-profile.yaml` 存在 → `validate_profile.py`；否则 `extract_profile.py` 从用户 `resume.tex` 抽取，并让用户确认/补充。学到的新事实**写回** YAML。
3. **匹配分析**（`references/jd-analysis.md`）— 解析 JD 为：硬性要求 / 加分项 / 职责 / ATS 关键词；逐项与 profile 的 tags/skills/metrics 匹配，分类为 **覆盖 / 部分 / 缺口**。缺口绝不编造填补，列出或反问用户。
4. **裁剪**（`references/tailoring-rules.md` 硬边界）— LLM 选择/重排 id、按 JD 词汇润色已有 bullet、突出最相关的真实指标，产出 `tailor.json`。
5. **填模板 + 编译** — `fill_template.py` → `resume.tex`；`detect_engine.sh` 探测引擎（缺失则引导安装并停下）；`render_pdf.sh` → `resume.pdf`。
6. **匹配报告** — `ats_check.py` 在**渲染后 PDF 纯文本**上做关键词命中检查；输出 `match-report.md`：覆盖表（要求→状态→证据 id）、ATS 命中表、补强审计（哪些被强调 vs 留作缺口）。

产物落到 `output/<公司>-<岗位>-zh-<日期>/`：`resume.pdf` + `resume.tex` + `tailor.json`（裁剪审计）+ `match-report.md`。

---

## 6. Tailoring Rules — 真实为主，合理补强（硬边界）

详见 `references/tailoring-rules.md`。

**允许（补强）：** 重排经历/bullet 顺序；按 JD 相关性筛选；用 JD 词汇润色已有 bullet 文案；把已有的真实 `metrics` 前置/突出；按 JD 重新归组技能；调整语气/详略。

**禁止（编造）：** 新增公司/职称/时间；编造 profile 里没有的 `metrics`；声称没有 `evidence_refs` 支撑的技能；夸大 level/years；把 JD 关键词写进简历却无真实证据支撑。

**执行机制：** 每条进入简历的内容都必须能追溯到 profile 的 id；`tailor.json` 记录 `源id → 最终文案`；JD 关键词只有解析到证据才能出现，否则进缺口清单或转为向用户提问。匹配报告含“补强审计”段，让用户看清哪些被强调、哪些留作缺口。

---

## 7. Engine / Dependency Strategy（依赖策略）

- v1 唯一硬依赖：一个 XeLaTeX 引擎（**tectonic** 推荐，单二进制、按需下载宏包、跨平台；或 TeX Live 的 xelatex）。
- `detect_engine.sh` 早执行；缺失时按 OS 给出安装命令（mac: `brew install tectonic`；Debian/Ubuntu: `apt install texlive-xetex` 或 tectonic release；Windows: `winget`/scoop），**停下等待用户安装**，不静默降级。
- 模板字体已内置、走相对路径 → 跨机可移植，不依赖系统字体。
- Python 依赖 stdlib 优先；YAML 解析若需 pyyaml 则写入 requirements 并做缺失提示。

---

## 8. Testing Strategy（测试）

- **单元**：`test_fill_template.py`（占位符替换 + LaTeX 特殊字符转义 `& % $ # _ { } ~ ^ \`）、`test_validate_profile.py`（合法 profile 通过、坏 fixture 被拒）。
- **集成（冒烟）**：`examples/sample-jd.txt` + `examples/sample-master-profile.yaml` → 跑通全流程 → 产出非空 `resume.pdf` + `match-report.md`。
- **可行性已验证**：用户模板经 tectonic 零改动编译成功（236KB PDF，中文/字体/排版正常）。
- **负向**：模拟“无引擎” → `render_pdf.sh` 返回非0并给出安装指引，不崩溃。
- CI：`.github/workflows/ci.yml` 在干净 runner 上跑单元测试。

---

## 9. Boundaries（边界）

**总是做：** 探测依赖后再动手；产物带审计（tailor.json + 报告）；学到的事实写回素材库（经用户确认）；尊重 `exclude_ids`/照片可选。
**先问再做：** 任何需要联网发布的动作（v1 无）；覆盖用户已有 `master-profile.yaml`；安装系统软件（给命令让用户自己执行）。
**绝不做：** 编造任何经历/数字/技能；把无证据的 JD 关键词塞进简历；把含 PII 的素材库提交进 git。

---

## 10. Verification（如何验收 v1）

```bash
# 1. 引擎探测
bash scripts/detect_engine.sh            # → {"engine":"tectonic","available":true}

# 2. 从用户简历抽取素材库
python3 scripts/extract_profile.py myCV__agent_/resume.tex -o data/master-profile.yaml
python3 scripts/validate_profile.py data/master-profile.yaml   # 通过，列软提醒

# 3. 单元测试
python3 -m pytest tests/                 # 绿

# 4. 全流程（给一份中文 JD）
#   → output/<公司>-<岗位>-zh-<日期>/ 下生成 resume.pdf + match-report.md
#   人工核对：PDF 排版正常；报告含覆盖表 + ATS 命中表 + 补强审计；
#   抽查每条 bullet 都能在 master-profile.yaml 里找到来源（无编造）。

# 5. 负向：临时让 PATH 无引擎 → render_pdf.sh 返回非0 + 安装指引
```
