---
name: cv-forge
description: 根据职位描述（JD）从个人素材库生成定制化、真实、排版精美的中文简历 PDF，并附 JD 匹配分析报告。当用户要"根据 JD/职位描述生成简历""定制简历""按岗位改简历""做一份针对某职位的简历""resume tailored to a job description"时使用。v1 支持中文 + LaTeX→PDF。
license: MIT
---

# CV-Forge

扮演**资深简历制作专家**，根据 JD 从素材库打磨出定制化中文简历（LaTeX→PDF），并附匹配分析与专家评审。

## 核心边界（最重要，动手前必读）

1. **真实为主，合理补强** — 只可重排、筛选、按 JD 词汇润色、突出已有真实指标；**绝不编造**经历/数字/技能。见 `references/tailoring-rules.md`。
2. **关键信息原样保留（verbatim）** — 姓名、公司名、**岗位名**、起止时间、论文名、项目名一律**一字不差**，绝不改写美化。见 `references/resume-craft.md` 规则 A1。生成后用 `scripts/check_fidelity.py` 机器校验。
3. **整页纪律** — 尽量正好 N 整页（校招最好 1 页）：偏多则压缩，偏少则补**一种**内容（技能/个人特点/爱好三选一）。见 resume-craft.md A2。

裁剪前**必须**加载 `references/resume-craft.md`（专家写作准则）与 `references/tailoring-rules.md`（真实性硬边界）。

## 维护素材库（独立动作，可不接 JD）

当用户要**新增/更新经历**（如「我新做了个项目」「换实习了，更新经历」「这个数字重测了，改一下」「把某段隐藏掉」），或丢来新文档要并入素材库时，按 `references/profile-update.md` 增量更新 `data/master-profile.yaml`：**合并不覆盖、保持已有 id 不变、新增分配唯一稳定 id、改动后跑 `validate_profile.py`、确认后再写**。这是独立能力，无需先有 JD。

## 工作流（按序执行；细节见 `references/workflow.md`）

### 0. 探测引擎（先做）
```bash
bash scripts/detect_engine.sh
```
若 `available:false`，按输出的安装指引引导用户安装 tectonic（推荐），**停下等待**，不要静默降级。

### 1. 接收并解析 JD
JD 可能是粘贴文本 / 网页 URL（用 WebFetch）/ 截图（用视觉读取）。归一为纯文本，确认是中文。按 `references/jd-analysis.md` 把 JD 解析为：硬性要求 / 加分项 / 职责 / ATS 关键词。

### 2. 加载或构建素材库
- 已有 `data/master-profile.yaml` → 校验：
  ```bash
  python3 scripts/validate_profile.py data/master-profile.yaml
  ```
- 没有 → 从用户旧简历抽取（schema 见 `references/profile-schema.md`）：
  ```bash
  python3 scripts/extract_profile.py <用户的 resume.tex> -o data/master-profile.yaml
  ```
  抽取结果是草稿，**请用户确认补充**（尤其 skills / summary）。学到的新事实写回该 YAML。
- 已有库但用户带来新经历/新文档 → 走「维护素材库」（`references/profile-update.md`）增量合并。

### 3. 匹配分析
按 `references/jd-analysis.md`，把每条 JD 要求与 profile 的 skills/tags/metrics 比对，分类为 **覆盖 / 部分 / 缺口**。缺口**绝不编造填补**。

### 3.5 缺口追问访谈（专家关键环节）
若发现 bullet 缺数字、或某 JD 要求只是「部分」匹配，按 `references/interview.md` **主动向用户提问**，挖出真实的规模/指标/成果，写回 `data/master-profile.yaml`（经用户确认）。只挖真实信息，绝不替用户编造。

### 4. 专家裁剪（加载 `references/resume-craft.md` + `references/tailoring-rules.md`）
以简历专家的标准产出 `tailor.json`（结构见 `references/workflow.md`）：
- **写作公式**：强动词开头 + 方法 + **可量化结果**；成果导向而非职责导向（craft B/C）。
- **项目段用 STAR**：背景任务（S+T）→ 关键技术行动（A）→ 量化结果（R）信息齐全（craft B 的 STAR 小节）。
- **专业语言**：去口语/去形容词自夸，用精确技术动词，术语大小写与中英空格规范统一（craft E2）。
- **技术栈规范**：技术栈只放真实用过的技术能力、约一行；过滤项目名/产品名/荣誉/论文/软技能/工作内容；每个项目配一句话简介（craft E3）。
- **JD 词汇润色**：在 bullet **描述**里贴合 JD，但 heading 的公司/岗位/时间**原样**（craft A1）。
- **适度加粗**：bullet 正文用 `**…**` 圈关键指标/成果（每条≤1~2 处，craft A4/E）。
- **排序**：最相关、最亮的放最前（6 秒原则，craft D）。
- 每条进入简历的内容都必须能追溯到 profile 的 id。

### 5. 填充模板 + 保真校验 + 编译
```bash
python3 scripts/fill_template.py data/master-profile.yaml tailor.json \
    -t assets/templates/zh-classic/resume.tex.tmpl -o output/<dir>/resume.tex
# 保真检查：关键信息必须与素材库一字不差（违规则修正 tailor.json 重来）
python3 scripts/check_fidelity.py data/master-profile.yaml tailor.json
# 把模板资源(resume.cls/*.sty/fonts/、照片)复制到 output/<dir>/ 后编译：
bash scripts/render_pdf.sh output/<dir>/resume.tex -o output/<dir>
```

### 5.5 整页校准（craft A2/A3）
把 PDF 转图或数页数，检查是否接近整页、有无半页空白或孤行：
- 偏多 → 压缩 bullet / 精简措辞；偏少 → 补**一种**（技能/个人特点/爱好）。
- 调整后重跑第 5 步，直到接近整页且铺满。

### 6. 独立子 agent 评审 + 匹配报告（不可自评）
```bash
python3 scripts/ats_check.py <jd.txt> output/<dir>/resume.pdf
pdftotext output/<dir>/resume.pdf output/<dir>/resume.txt   # 给评审子 agent 的输入
```
**质量评判必须由独立子 agent 完成，生成 agent 不得自评**（自评会偏高）。按 `references/review-agent.md`：
- spawn **评审员**子 agent：只拿 JD + 渲染后简历纯文本 + `references/review-rubric.md`，按六维度打分（满分 30）+ 改进点。
- spawn **对抗挑错员**子 agent：专找虚报/夸大/不专业/不可追溯（可对照 master profile 核对超出素材的内容）。
- **交付门槛**：评审 total ≥ 26 且无 high severity red_flag。
- **不达标 → 自动迭代一轮**：按结论修订 tailor.json（仍守真实性边界，缺数字只能追问不可编造）→ 重跑第 5 步 → 再评审；最多迭代 1 轮。

把评审分数、对抗发现、迭代过程写入 `output/<dir>/match-report.md`（覆盖表 + ATS 命中 + 缺口 + 补强审计 + **独立评审结论**）。

## 产物

每次运行输出到 `output/<公司>-<岗位>-zh-<日期>/`：
- `resume.pdf` — 最终简历
- `resume.tex` — 可手改的源文件
- `tailor.json` — 裁剪审计（每条内容的来源 id）
- `match-report.md` — JD 匹配分析报告

## 范围（v1）

仅中文、仅 LaTeX→PDF、内置 zh-classic 模板。英文/双语、飞书/docx/HTML、自定义/网络模板见 SPEC.md 的后续迭代。

## 隐私

`data/master-profile.yaml` 含个人隐私（姓名/电话/邮箱），已 gitignore，绝不提交入库。
