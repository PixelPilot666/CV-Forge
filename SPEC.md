# SPEC — `CV-Forge` Skill (v1)

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
| `python3 scripts/page_metrics.py <resume.pdf>` | 读 `pdfinfo` 页数 + `pdftotext -bbox` 末页文本框算 `fill_ratio`，输出 JSON（§11.3）| 0=成功，2=工具或输入缺失（报告度量不可用）|
| `python3 scripts/polish_gate.py --state <polish-state.json> --metrics <m.json> --review <r.json> --critic <c.json> --target-pages <N>` | 按 §11.6–§11.9 做三态裁决（pass/revise/deliver-best），回写 state，stdout 打印 decision/reason/deliverable | 0=终止（看 decision），10=revise，2=输入缺失/异常 |
| `python3 scripts/finalize_delivery.py --state <polish-state.json> --pdf <resume.pdf> --out-dir <out>` | 只按终止 state 生成正式版或 DRAFT 文件名并输出报告摘要 | 0=成功，2=输入缺失/异常 |

> 裁剪（tailor）这一步由 **LLM 判断**完成，不是脚本：agent 读 JD + profile，产出一个 `tailor.json`（选了哪些 id、每条 bullet 的最终文案、章节顺序），再交给 `fill_template.py`。脚本只做确定性的“填充 + 转义 + 编译”。

---

## 3. Project Structure（项目结构）

```
CV-Forge/
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

---

## 11. Polish Loop & Termination（打磨循环与终止保证）

> 本章把 SKILL.md §5.5「整页校准」与 §6「评审迭代」**合并为唯一一个外层「打磨循环」**，建模为带**有界整数计数器**的确定性状态机，给出**可机器判定的终止保证**（§11.9）。
>
> **本章覆盖并取代的旧文**（实现时按本章重写，本章为权威定义）：
> - SKILL.md §5.5 全段（「调整后重跑第 5 步，直到接近整页且铺满」）；
> - SKILL.md §6 与 `references/review-agent.md`「主流程如何使用结论」中「不达标 → 自动迭代一轮 … 最多迭代 1 轮」段；
> - `references/review-rubric.md`「评分与处置」中「任一维度 ≤2 必须修订该维度后再交付」「total≥26 可交付」等措辞——这些不再表示「禁止交付」，而是按本章 §11.7/§11.8 的三态裁决决定**交付哪一版**并在报告标注。**两份文档冲突时，以本章为准。**

### 11.1 设计动机（为什么必须重做）

旧编排有**两个独立迭代点**叠加**三条互相打架的硬约束**，会制造一个可能无解的目标：

| 旧问题 | 后果 |
|---|---|
| §5.5「重跑第 5 步直到接近整页且铺满」 | 无上限循环；「偏多压缩 / 偏少补一种」是一对相反操作、又无容差带，在 ~0.9 页 ↔ ~1.1 页之间反复横跳 |
| §6「不达标自动迭代一轮 … 最多 1 轮」 | 上限只写在散文里、是软约束，靠 agent 记忆约束 |
| 三条硬约束打架：① 整页铺满 ② 真实性边界（profile 没有的绝不编造）③ 评审 `total≥26` 且无 high red_flag | 素材本就不足时：铺不满、分上不去、又不准编造 → 既「改也改不好」又「停也不让停」 |
| 评审分非确定性（每轮 spawn 的评审员给分/改进点不同） | 靶子在移动；与页面循环嵌套共振（评审迭代重跑第 5 步 → 触发页面循环 → 页数变 → 再评审） |

**根治思路**：把「停不停、停在哪一版」从 agent 的主观判断变成对**落盘状态文件 + 脚本退出码 + 整数计数器**的机器判定。所有度量（页数、是否有 actionable 项、是否达标）都有唯一的脚本来源，agent 不得目测、不得凭记忆。任意输入下，循环都在有限步内必然进入唯一交付态。

### 11.2 硬规则（违反即不合格，优先级最高）

- **P1 单循环单计数器**：单页校准与评审迭代合并为**一个**外层打磨循环，共用一个 `round` 计数器，硬上限 `MAX_ROUNDS = 1`。页面校准、保真修复、编译重试各自再有**独立的有界子计数器**（§11.5 常量表），均落盘。
- **P2 状态落盘，不靠记忆**：「已迭代几轮 / 上一版几页 / 最优版是谁 / 最后评审对应哪一轮」一律写入 `$OUT/polish-state.json`（schema 见 §11.4），**每次决策前先读后写**。这些是文件里的事实，不是 agent 的印象。
- **P3 度量必须机器产出，禁止目测**：页数与填充比由脚本 `page_metrics.py` 确定性计算并落盘（§11.3）；评审发现的「可改 / 需真实数据」分类由评审子 agent 在输出 JSON 时**自带机器字段**、再由 `polish_gate.py` 计数（§11.6）。页数、actionable_count 与达标门槛只读脚本/落盘值，**agent 不得自报、不得凭印象**。
- **P4 页数硬约束、填充率软提示**：目标为 1 页，`pages_int==page_target` 才满足页面门槛；超过 1 页只允许压缩，累计上限 `CAL_MAX = 2`。`fill_ratio` 只产生 `sparse` / `dense` 提示，不参与评分、best 选择或 `deliverable` 判定，且不得驱动添加低价值内容。
- **P5 评审发现两分类（斩断徒劳迭代）**：只有「无需新事实即可修」（`actionable`）的发现才触发迭代；「需要真实数据才能修」（`needs-fact`）改走 `interview.md` 追问或如实写进 `match-report.md` 缺口段，**不消耗迭代轮次**（§11.6）。
- **P6 真实性违规优先删除，绝不带 high red_flag 出门**：凡「虚报 / 夸大原创性 / 超出素材 / 技术栈违规」类 high severity red_flag，其修复是**删除/改写该内容**——删除不引入新事实，永远是 `actionable`，**必须修**。若 `round` 用尽仍残留 high red_flag，终止但只能输出标记为 `NOT-READY` 的 DRAFT；绝不能输出正式 `resume.pdf`。
- **P7 单调改进 + 交付快照一致**：保留 `best` 作为迄今综合最优的比较快照；下一版只有严格更优时才覆盖它。另以 `selected` 记录刚完成评审、磁盘上实际存在的 PDF；最终分数、high flag、页数和文件名一律读取 `selected`，避免旧 best 元数据指向已被覆盖的 PDF。
- **P8 必然进入交付态**：无论是否达 26 分，循环结束必然进入交付。是否「可投递」是**独立的机器可判定标志** `deliverable`（§11.8），未达门槛的产物以显式标记区分，绝不与达标产物同名同位静默交付。

### 11.3 页数与填充比：机器度量（替换「肉眼判断」）

`pages_int` 是页面交付硬约束；`fill_ratio` 只是最后一页内容位置的近似提示。本章用确定性脚本 `page_metrics.py` 统一产出二者：

- 输入：`$OUT/resume.pdf`。
- 计算：`pages_int = pdfinfo 的 Pages`；`fill_ratio = (pdftotext -bbox 取最后一页文本框最底边 y / 该页版心高度)`，结果按两位小数 floor；`pages_float = (pages_int - 1) + fill_ratio`。
- 输出：JSON `{"pages_int":1,"fill_ratio":0.94,"pages_float":0.94}`，并由调用方写回 `polish-state.json` 的 `last_pages` / `last_fill_ratio`。

**硬规则：**
1. `pages_int`、`fill_ratio` 与 `pages_float` **只能由 `page_metrics.py` 产出并落盘**，agent 不得手传、不得目测。
2. `Pages == N` 视为页数达标，`Pages > N` 触发压缩；本技能的校招/实习默认目标 `N=1`，作为 `polish_gate.py` 的显式入参。
3. `fill_ratio < 0.75` 记 `sparse`，`fill_ratio > 0.98` 记 `dense`，其余无提示。提示只进入 state/report；单页偏空仍可投递，不自动补兴趣、个人特点、普通奖项、重复 bullet 或无关技术。
4. 度量工具不可用时必须报告不可用，不得凭目测宣称页数达标。

### 11.4 状态文件 schema（`$OUT/polish-state.json`）

机器可读，由编排层在每次 BUILD/CALIBRATE/REVIEW/REVISE 后**原子写入**（先写临时文件再 rename）。首次进入若文件不存在，以 `round=0, cal=0, *_fix=0, last_dir=none, best=null` 初始化。

```json
{
  "schema": "cv-forge/polish-state@1",
  "round": 0,
  "max_rounds": 1,
  "page_target": 1,
  "density_warning_band": [0.75, 0.98],
  "cal": 0, "max_cal": 2,
  "fidelity_fix": 0, "max_fidelity_fix": 2,
  "build_retry": 0, "max_build_retry": 1,
  "last_pages": null,
  "last_fill_ratio": null,
  "last_density_warning": null,
  "last_dir": "none",
  "last_score": null,
  "last_high_flags": null,
  "last_review_round": null,
  "has_actionable": null,
  "best": {
    "round": null, "score": null, "pages": null, "fill_ratio": null,
    "high_flags": null, "page_ok": null,
    "tex_path": "resume.tex", "pdf_path": "resume.pdf", "tailor_path": "tailor.json"
  },
  "selected": null,
  "history": [],
  "needs_fact": [],
  "unfixed_actionable": [],
  "terminated": false,
  "deliverable": null,
  "decision": null,
  "delivery_reason": null
}
```

| 字段 | 类型 | 含义 / 约束 |
|---|---|---|
| `round` | int | 已完成的评审迭代轮次；`0`=初稿，**只增不减**，上限 `max_rounds` |
| `cal` | int | 本轮内页面校准动作次数；**进入新 round 时归 0**；上限 `max_cal` |
| `last_dir` | enum | 旧状态兼容字段；新页面策略只会压缩超页内容，不再执行 `expand` |
| `fidelity_fix` | int | BUILD 内保真修复次数；上限 `max_fidelity_fix`（§11.5）|
| `build_retry` | int | BUILD 编译失败重试次数；上限 `max_build_retry`（§11.5）|
| `last_pages` / `last_fill_ratio` | float | 由 `page_metrics.py` 产出；前者参与页数硬门，后者仅生成提示（§11.3）|
| `last_density_warning` | enum/null | `sparse` / `dense` / `null`，只用于报告，不参与裁决 |
| `last_score` / `last_high_flags` | int | 上一版评审 total（满分 30，非确定性）/ high severity red_flag 计数 |
| `last_review_round` | int/null | 评审对应的候选 round；正式交付时必须等于当前 `round`，防修订后复用旧评审 |
| `has_actionable` | bool | 上一版是否存在 actionable 发现；由 `polish_gate.py` 读评审 JSON 的 `category` 字段计数得出（§11.6）|
| `best` | object | 迄今最优产物快照与文件路径（P7）；仅被严格更优者覆盖；初始为 `null`（视为最差，任何已评分真实版必然严格优于它） |
| `selected` | object/null | 终止时刚评审、磁盘上实际存在的 PDF 快照；finalizer 与报告以它为准，旧 state 缺失时才回退 `best` |
| `history` | array | 每步 `{round,pages,fill_ratio,action,score,high_flags}` 追加，供审计与同批次比较；只增不改 |
| `needs_fact` | string[] | needs-fact 类发现原文，进 match-report 缺口段（P5）|
| `unfixed_actionable` | string[] | 因 round 触顶未改的 actionable 项，进 match-report（让用户知道哪些可改未改）|
| `terminated` / `deliverable` | bool | 终止标志 / **是否可直接投递**（P8）|
| `decision` / `delivery_reason` | enum | 最近一次三态裁决 / 终止原因枚举（§11.7）|

### 11.5 常量（硬上限，机器判定）

| 常量 | 值 | 含义 | 备注 |
|---|---|---|---|
| `MAX_ROUNDS` | **1** | 评审迭代至多 1 轮（首版 + 至多 1 次重做） | 把旧「最多 1 轮」从散文软约束固化为计数器上限 |
| `CAL_MAX` | **2** | 单轮内超页压缩动作上限 | 只处理 `pages_int > page_target`，不因偏空扩写 |
| `FIDELITY_MAX` | **2** | 单轮内 BUILD 保真修复上限 | 防 `check_fidelity` 反复润色命中失败的自环（§11.6 BUILD）|
| `BUILD_RETRY_MAX` | **1** | 单轮内编译失败重试上限 | 防 `build_resume.sh` 非 0 的未建模回边 |
| `DENSITY_WARN_LO` / `DENSITY_WARN_HI` | **0.75 / 0.98** | 稀疏/拥挤提示阈值 | 只写报告，不影响评分或交付 |
| `DELIVER_SCORE` | **26** | 达标门槛（评审 total） | 与 review-rubric 一致 |
| `SOFT_FLOOR` | **24** | 软底线：达不到 26 但 ≥24、无 high red_flag、且页数正确时允许当前已评审版作为「可投递」 | 给「素材边界内可用版本」一个体面出口 |

### 11.6 状态机（七态，唯一吸收态 DELIVER）

一次「打磨迭代」= BUILD（填模板+保真+编译，内嵌有界保真修复与编译重试）→ CALIBRATE（只处理超页，内嵌有界）→ REVIEW（独立评审，每轮恰好一次）→ 三态裁决。

```
[INIT] → [BUILD] ⟲(check_fidelity 失败 & fidelity_fix<MAX)         ← 不计 round/cal
                 ⟲(编译失败 & build_retry<MAX)
            │
            ├─(fidelity_fix 或 build_retry 触顶) ───────────────────► [DELIVER]（标注冲突/编译失败，交付上一可编译版或草稿）
            │
            ▼ (编译成功，page_metrics 落盘)
        [CALIBRATE] ⟲(cal<CAL_MAX & pages_int>N)→回 BUILD            ← cal+=1
            │
            ▼ (pages_int==N / cal 触顶)
        [REVIEW] → polish_gate.py 三态裁决
            │
   ┌────────┼─────────────────────────┐
 pass│   revise│(round<MAX & has_actionable & 严格更优 & 无未删的 high)   │deliver-best
   ▼          ▼                          ▼
[DELIVER]  [REVISE]→round+=1,cal=0→回 BUILD   [DELIVER]
(吸收态)                                      (吸收态)
```

各态硬规则：

- **BUILD**：`fill_template.py` → `check_fidelity.py` → `build_resume.sh`。
  - **保真自环有界**：`check_fidelity.py` 返回 1 时修正 `tailor.json` 并 `fidelity_fix += 1`（不计 round/cal）；触顶 `FIDELITY_MAX` 后**不再回 BUILD**，而是把逐条违规原样写进 match-report「需用户核对的 verbatim 冲突」段并转 DELIVER（`deliverable=false`）。修正时**只允许把 heading 改回与 profile 一字不差**（A1），不得借机润色岗位名/全角改半角——这正是 `expected not in heading_text` 反复命中失败的根因。
  - **编译失败有界**：`build_resume.sh`/`render_pdf.sh` 返回非 0（≠引擎缺失的 3）时 `build_retry += 1`，修 tex 或回退 `best` 那版重编译；触顶 `BUILD_RETRY_MAX` 仍失败 → 转 DELIVER 并在报告标注「编译失败，交付上一可编译版」；首版即编译失败且无 best → `deliverable=false`，只交付源文件 + 报告。引擎缺失（退出码 3）按 §0/§7 走安装引导、**不进本循环**。
- **CALIBRATE**：页面校准子过程（§11.7），只在超过目标页数时删减内容，`cal` 有界；单页偏空不动作。
- **REVIEW**：spawn 独立评审员 + 对抗挑错员（沿用 `review-agent.md` 的隔离输入），**评审只跑一次/轮**，不在 REVIEW 内自循环。评审/对抗 JSON 必须扩展为每条发现自带机器字段（见下「评审发现分类」），写回 `last_score`/`last_high_flags`/`last_review_round`/`has_actionable`。修订后必须从新版 PDF 重新生成两份评审，正式交付时 `last_review_round==round`。
- **REVISE**：仅按 actionable 发现修订 `tailor.json`（不引入任何新事实），`round += 1`、`cal = 0`（`last_dir` 保留），回 BUILD。
- **DELIVER**：唯一终态，**无出边**；按 §11.8 输出 `selected` 对应的当前 PDF + 写报告，`best` 只留作比较审计。

**评审发现分类（机器可判定，斩断「分上不去→再改→还上不去」）**：

| 类别 | `category` 字段值 | 判据（评审子 agent 按可枚举清单贴标，polish_gate 只读字段计数，不做语义判断） | 是否触发 REVISE |
|---|---|---|---|
| **可改类** | `actionable` | 排序/前置不当、措辞不专业、加粗过多/整句加粗、术语大小写与中英空格、技术栈违规（E3 混入项目名/产品名/荣誉/软技能/内置库）、冗余可删、AI 腔句式、孤行、**以及删除/改写夸大原创性或超出素材的表述**（删除不引入新事实） | **是**（且仅当 `round<MAX_ROUNDS`） |
| **需真实数据类** | `needs-fact` | 量化不足（缺真实数字）、某 JD 硬性要求在 profile 是缺口、规模/成果无证据**且删了不构成违规**的补强诉求 | **否**：走 `interview.md` 追问 / 写进缺口段 |

**硬规则：**
- 评审员 / 对抗挑错员**必须**在输出 JSON 里给每条 `improvement` / `red_flag` 附 `category: "actionable"|"needs-fact"` 与 `axis`（命中维度）；`polish_gate.py` 读 `category` 计 `actionable_count`，**不由生成 agent 事后归类**（堵住「想改就标 actionable、想停就标 needs-fact」）。`review-agent.md` 的输出 schema 据此扩展。
- **兜底分类规则**（脚本侧）：凡 `red_flag` 的 `severity == "high"` 一律优先强制 `actionable`（先删除或降级当前可疑表述，见 P6）；只有 high 清零后，未来补证诉求才另记 `needs-fact`。其余发现凡命中「缺数字/无证据/规模/JD 要求缺口」关键词或 `needs_new_fact==true`，强制 `needs-fact`。消除同一条按需归类。
- 若某轮所有未达标项都是 `needs-fact`（`actionable_count==0`），`polish_gate.py` 直接 `deliver-best`，**不消耗迭代轮次**。
- 页面填充率不是评分 axis，不会因 `sparse` 触发 actionable；素材偏少只写提示或进入访谈，不消耗 `round`。

### 11.7 页面校准 + 单调改进（页数硬门、严格偏序）

**页面校准（CALIBRATE 子过程）硬规则：**
1. **页数优先**：`pages_int == N` 即页面达标，直接转 REVIEW；默认 `N=1`。
2. **只压不扩**：`pages_int > N` 时删弱相关、重复或组件清单化内容，再重编译量页（`cal += 1`）。不得通过缩小到难读的字号、行距或边距规避页数约束。
3. **不因偏空动作**：`pages_int == N` 时无论 `fill_ratio` 高低都不扩写；`sparse` / `dense` 只进入报告。
4. **次数上限**：`cal` 达 `CAL_MAX=2` 即停并转 REVIEW；若仍超过 N 页，gate 终止为不可投递 DRAFT。

**单调改进偏序（`polish_gate.py` 判「严格更优」，字典序）：**
1. `high_flags` **更少者优**（0 优于 ≥1）——真实性/安全第一，且 high_flags 是可追溯的确定性事实，优先于噪声分数。
2. `page_ok`（`pages_int == N`）**真者优**——页数是硬闸；仅候选消除 high red_flag 时可优先保留安全但超页的 DRAFT。
3. `med_flags` **更少者优**。
4. `total` **高者优**；前四档全平即并列，不用 `fill_ratio` 打破平局。

**硬规则：**
- 仅当候选在上述偏序中**严格胜出**才覆盖 `best`；否则回退 best。
- **算子顺序明确**：`polish_gate.py` 先用「候选 vs 旧 best」做 `revise` 判定（候选严格更优 且 `actionable_count≥1` 且 `round<MAX` → revise），REVISE 入口再更新 best 快照。这样 MAX_ROUNDS=1 的唯一一轮不会因「先更新 best 致候选==best 永不更优」而成死代码。
- **保护已修复版本不被噪声推翻**：若候选相对 best **减少了 high/med red_flag 数**（确定性事实），即使 `total` 因评审非确定性偶然低 1~2 分，仍判候选严格更优（red_flag 减少优先于 total），不回退到带 red_flag 的旧版。
- **分数语义**：当前候选的 `DELIVER_SCORE` 判定及终止时的 `SOFT_FLOOR` 判定使用本轮单次评审结果；它会写入 `selected`，若严格更优也写入 `best`。报告读取 `selected`，并标注分数为「单次独立评审快照、非确定性」。

### 11.8 三态裁决与交付出口（`polish_gate.py`，机器可判定）

`polish_gate.py` 读 `page_metrics.py` 输出 + 评审/对抗 JSON（含 `category`）+ `polish-state.json`，输出**且仅输出**三态之一并回写状态文件。三态对全部输入**完备且互斥**：

| `decision` | 退出码 | 触发条件（全部为机器可判定布尔式，按序取首个命中） | 编排层动作 |
|---|---|---|---|
| `pass` | 0 | 当前候选 `high_flags==0` **且** `total≥DELIVER_SCORE(26)` **且** 六维均 >2 **且** `page_ok` | 写入 `selected` → DELIVER，`deliverable=true`，`reason=pass` |
| `revise` | 10 | `decision≠pass` **且** `round<MAX_ROUNDS` **且** `actionable_count≥1` **且** 候选严格优于 best **且** 非振荡 | REVISE（`round+=1`），重跑 BUILD |
| `deliver-best` | 0 | 其余一切（`round≥MAX_ROUNDS` / `actionable_count==0` / 候选不优于 best / `cal` 触顶 / 页数不符 等） | 终止并写入当前 `selected` → DELIVER；`best` 仅留审计，`reason` 取对应枚举 |

**退出码约定**（与既有脚本 0/1/2/3 风格一致）：`0`=终止（看 `decision` 决定交付哪一版），`10`=继续迭代（agent 才允许再跑一轮第 5 步），`2`=输入缺失/异常（页数或评审 JSON 读不到、JSON 非法）。`decision` 字段是裁决依据，退出码仅供 SKILL.md 分支。

**`deliver_reason` 枚举**：`pass` / `max_rounds_reached` / `only_factual_gaps` / `no_improvement` / `calib_exhausted` / `page_count_mismatch` / `fidelity_conflict` / `build_failed` / `review_unavailable`。

**异常出边（堵住未建模回边）：**
- `polish_gate.py` 退出码 `2`（评审子 agent spawn 失败/超时/返回非法 JSON，IDE 等无子 agent 环境高发）→ **不重试**，直接 `deliver-best`（best 为空时 best=当前唯一版），`reason=review_unavailable`，报告标注「评审未能执行，未经独立评审交付」，`deliverable` 按 §11.8 下方门槛另判。**任何脚本失败都单向汇入 DELIVER，杜绝「裁决失败→自由重试」。**

**`deliverable`（是否可直接投递）独立判定** —— **终止 ≠ 可投递**：

```
deliverable = (selected.high_flags == 0) AND (selected.page_ok == true) AND (selected.score >= SOFT_FLOOR)
```

- `deliverable == true`：交付 `$OUT/resume.pdf`，正常投递版。
- `deliverable == false`：**仍终止、仍交付**，但产物以 `$OUT/resume.DRAFT.pdf` 命名（不与达标产物同名同位），且 `match-report.md` 顶部加显著横幅 `⚠️ 未达交付门槛 / NOT-READY-TO-SUBMIT`，逐条列出原因（页数不符 / 分数偏低 / 残留 high red_flag / 未完成新版评审）与**需用户补的真实信息**。
- 终止后调用 `finalize_delivery.py`；它只信 state。只有 `terminated=true`、`deliverable=true`、`selected` 无 high flag 且 `last_review_round==round` 才保留 `$OUT/resume.pdf`，否则统一输出 `$OUT/resume.DRAFT.pdf`，并生成供报告原样引用的 JSON 摘要。

### 11.9 终止保证（Termination Guarantee）

**断言：对任意 JD 与任意 profile（含素材严重不足），打磨循环都在有限步内到达唯一吸收态 `DELIVER`，且交付当前已评审的 `selected` 产物。** 证明（良基性 / well-foundedness）：

| 计数器 / 出边 | 单调性与上界 | 覆盖的回边 |
|---|---|---|
| `round` | 仅在 REVISE 中 `+1`，从不回退，上界 `MAX_ROUNDS=1` | 评审迭代 |
| `cal` | 仅在 CALIBRATE 动作时 `+1`，上界 `CAL_MAX=2`，进入新 round 归 0（属新一段有界递增序列） | 页面校准 BUILD↔CALIBRATE 回边 |
| `fidelity_fix` | 仅在 BUILD 保真失败时 `+1`，上界 `FIDELITY_MAX=2` | check_fidelity BUILD→BUILD 自环 |
| `build_retry` | 仅在 BUILD 编译失败时 `+1`，上界 `BUILD_RETRY_MAX=1` | 编译失败 BUILD→BUILD 自环 |

1. **无空转回边**：每条非终态出边要么推进某个上述计数器、要么直接转 DELIVER；不存在「既不推进任何计数器、又不去 DELIVER」的边（页数达标时直接转 REVIEW；脚本异常单向汇入 DELIVER）。每个子循环都被独立有界计数器封顶。
2. **路径长度被常数界定**：每轮内 BUILD 次数 ≤ `(CAL_MAX+1) + FIDELITY_MAX + BUILD_RETRY_MAX`，REVIEW 每轮恰好 1 次；总路径长度 ≤ `(MAX_ROUNDS+1) × [ (CAL_MAX+1)+FIDELITY_MAX+BUILD_RETRY_MAX 次 BUILD + 1 次 REVIEW ]` = **常数**。
3. **唯一吸收态可达**：`DELIVER` 是唯一无出边状态；三态中 `pass`/`deliver-best`（退出码 0）在任一计数器触顶或裁决非 `revise` 时必被取到，`revise` 受 `round<MAX_ROUNDS` 封死至多取一次。故 `DELIVER` 必达。
4. **终止与达标解耦**：达标走 `pass`、不达标走 `deliver-best`，二者皆终止。**不存在「既改不好又停不下」的状态。**

**所有停止条件汇总（每一条都可机器判定，取代「直到满意」）：**

| 停止条件 | 机器判据（来源） | 落到的 `reason` |
|---|---|---|
| 达标交付 | `total≥26 ∧ 六维均>2 ∧ high_flags==0 ∧ page_ok`（评审 JSON + page_metrics + state） | `pass` |
| 迭代轮次用尽 | `round≥MAX_ROUNDS=1`（state 计数器） | `max_rounds_reached` |
| 无可改项（全是缺数据） | `actionable_count==0`（评审 JSON 的 `category` 字段计数） | `only_factual_gaps` |
| 新版不优于 best | 偏序比较未严格胜出（state） | `no_improvement` |
| 页面校准次数用尽 | `cal≥CAL_MAX=2`（state 计数器） | `calib_exhausted` |
| 页数不符 | `pages_int != page_target`（page_metrics + state） | `page_count_mismatch` |
| 保真冲突无法在不编造下修好 | `fidelity_fix≥FIDELITY_MAX=2`（state） | `fidelity_conflict` |
| 编译反复失败 | `build_retry≥BUILD_RETRY_MAX=1`（render 退出码非 0） | `build_failed` |
| 评审不可用 | `polish_gate.py` 退出码 2（脚本异常） | `review_unavailable` |

### 11.10 命令 / 脚本接口（接 §2 风格）

| 命令 | 作用 | 退出约定 |
|---|---|---|
| `python3 scripts/page_metrics.py "$OUT/resume.pdf"` | 读 `pdfinfo` 页数 + `pdftotext -bbox` 末页文本框算 `fill_ratio`，输出 JSON 并供回写 state | 0=成功，2=工具或输入缺失（报告度量不可用） |
| `python3 scripts/polish_gate.py --state "$OUT/polish-state.json" --metrics <page_metrics.json> --review <reviewer.json> --critic <critic.json> --target-pages <N>` | 套用 §11.6–§11.9 规则做三态裁决，回写 state，stdout 额外包含 `page_ok`、`dimension_floor_ok` 与只读 `density_warning` | 0=终止（看 decision），10=revise，2=输入缺失/异常 |
| `python3 scripts/finalize_delivery.py --state "$OUT/polish-state.json" --pdf "$OUT/resume.pdf" --out-dir "$OUT"` | 只按终止 state 生成正式版或 DRAFT 文件名并输出报告摘要 | 0=成功，2=state/PDF 无效 |

> 实现说明：三个脚本均用 stdlib，无第三方依赖。它们只做**确定性度量、裁决与状态读写，不做任何 LLM 判断、不评分、不改写简历内容**。真实性边界、单页纪律与独立评审隔离继续保留。

### 11.11 交付出口（无论是否达标，必进交付态）

到达 `DELIVER` 时，**无条件**按 `deliverable` 标志输出对应产物（达标 → `resume.pdf`；未达标 → `resume.DRAFT.pdf`），并在 `match-report.md`「独立评审」段如实记录：

1. 最终采用版（`selected`）的 `total`、六维分、对抗挑错员全部 red_flag（含未修复的 high/med/low，**逐条列出原文 + 判据**，把主观严重度暴露给用户复核）；
2. `delivery_reason`、`round`、`last_review_round`、页数是否符合目标，以及 `density_warning`；
3. **未修复项**：`unfixed_actionable`（因 round 触顶未改的可改项）+ `needs_fact`（需真实数据的缺口）逐条列出；
4. **需用户补的真实信息**：所有 `needs-fact` 发现引导走 `interview.md` 补全后重跑；
5. `polish-state.json` 一并留在 `$OUT` 作「为何在此停下」的机器可核对审计。

> **总是做**：终止后运行 finalizer、输出 `selected` 对应的当前 PDF、写报告并留状态文件审计。**绝不**：为填页或追分而编造；带未删的 high severity red_flag 输出可投递 `resume.pdf`；以 agent 目测的页数替代脚本度量；修订后复用上一轮评审。
