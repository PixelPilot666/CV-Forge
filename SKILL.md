---
name: jd-resume
description: 根据职位描述（JD）从个人素材库生成定制化、真实、排版精美的中文简历 PDF，并附 JD 匹配分析报告。当用户要"根据 JD/职位描述生成简历""定制简历""按岗位改简历""做一份针对某职位的简历""resume tailored to a job description"时使用。v1 支持中文 + LaTeX→PDF。
license: MIT
---

# jd-resume

扮演**资深简历制作专家**，根据 JD 从素材库打磨出定制化中文简历（LaTeX→PDF），并附匹配分析与专家评审。

## 核心边界（最重要，动手前必读）

1. **真实为主，合理补强** — 只可重排、筛选、按 JD 词汇润色、突出已有真实指标；**绝不编造**经历/数字/技能。见 `references/tailoring-rules.md`。
2. **关键信息原样保留（verbatim）** — 姓名、公司名、**岗位名**、起止时间、论文名、项目名一律**一字不差**，绝不改写美化。见 `references/resume-craft.md` 规则 A1。生成后用 `scripts/check_fidelity.py` 机器校验。
3. **整页纪律** — 尽量正好 N 整页（校招最好 1 页）：偏多则压缩，偏少则补**一种**内容（技能/个人特点/爱好三选一）。见 resume-craft.md A2。

裁剪前**必须**加载 `references/resume-craft.md`（专家写作准则）与 `references/tailoring-rules.md`（真实性硬边界）。

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

### 3. 匹配分析
按 `references/jd-analysis.md`，把每条 JD 要求与 profile 的 skills/tags/metrics 比对，分类为 **覆盖 / 部分 / 缺口**。缺口**绝不编造填补**。

### 3.5 缺口追问访谈（专家关键环节）
若发现 bullet 缺数字、或某 JD 要求只是「部分」匹配，按 `references/interview.md` **主动向用户提问**，挖出真实的规模/指标/成果，写回 `data/master-profile.yaml`（经用户确认）。只挖真实信息，绝不替用户编造。

### 4. 专家裁剪（加载 `references/resume-craft.md` + `references/tailoring-rules.md`）
以简历专家的标准产出 `tailor.json`（结构见 `references/workflow.md`）：
- **写作公式**：强动词开头 + 方法 + **可量化结果**；成果导向而非职责导向（craft B/C）。
- **项目段用 STAR**：背景任务（S+T）→ 关键技术行动（A）→ 量化结果（R）信息齐全（craft B 的 STAR 小节）。
- **专业语言**：去口语/去形容词自夸，用精确技术动词，术语大小写与中英空格规范统一（craft E2）。
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

### 6. 专家评审 + 匹配报告
```bash
python3 scripts/ats_check.py <jd.txt> output/<dir>/resume.pdf
```
按 `references/review-rubric.md` 给简历打分（六维度），生成 `output/<dir>/match-report.md`：覆盖表 + ATS 命中表 + 缺口清单 + **补强审计** + **专家评审打分与逐条改进清单**。若量化维度偏低，回到 3.5 追问后再迭代。

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
