---
name: jd-resume
description: 根据职位描述（JD）从个人素材库生成定制化、真实、排版精美的中文简历 PDF，并附 JD 匹配分析报告。当用户要"根据 JD/职位描述生成简历""定制简历""按岗位改简历""做一份针对某职位的简历""resume tailored to a job description"时使用。v1 支持中文 + LaTeX→PDF。
license: MIT
---

# jd-resume

根据 JD 生成定制化中文简历（LaTeX→PDF），守住「真实为主、合理补强、绝不编造」的底线。

## 核心边界（最重要）

**真实为主，允许合理补强。** 只可重排、筛选、按 JD 词汇润色、突出已有的真实指标；**绝不编造**经历 / 数字 / 技能。详见 `references/tailoring-rules.md`——动手裁剪前**必须**先读它。

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
按 `references/jd-analysis.md`，把每条 JD 要求与 profile 的 skills/tags/metrics 比对，分类为 **覆盖 / 部分 / 缺口**。缺口**绝不编造填补**，列入报告或反问用户。

### 4. 裁剪（遵守 `references/tailoring-rules.md`）
选择 / 重排 profile 里的条目与 bullet id、按 JD 词汇润色已有文案、突出真实指标，产出 `tailor.json`（结构见 `references/workflow.md`）。每条进入简历的内容都必须能追溯到 profile 的 id。

### 5. 填充模板并编译
```bash
python3 scripts/fill_template.py data/master-profile.yaml tailor.json \
    -t assets/templates/zh-classic/resume.tex.tmpl -o output/<dir>/resume.tex
# 把模板资源(resume.cls/*.sty/fonts/)复制到 output/<dir>/ 后编译：
bash scripts/render_pdf.sh output/<dir>/resume.tex -o output/<dir>
```

### 6. 匹配报告
```bash
python3 scripts/ats_check.py <jd.txt> output/<dir>/resume.pdf
```
生成 `output/<dir>/match-report.md`：覆盖表 + ATS 命中表 + 缺口清单 + **补强审计**（哪些被强调/润色，确保透明可追溯）。

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
