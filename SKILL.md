---
name: cv-forge
description: 根据职位描述（JD）或通用岗位方向，从个人素材库生成定制化、真实、排版精美的中文简历 PDF，并附匹配分析与独立评审报告。四种入口都应触发本技能——① 按 JD 定制/改简历；② 生成某岗位族的通用简历（如 Agent/RAG、搜索/推荐）；③ 维护个人素材库，新增/更新/修正/隐藏经历，此入口无需 JD；④ 从旧简历或文档初始化素材库。只要用户在打磨简历内容、整理求职素材或做 JD 匹配，即使没明说“定制简历”也应使用本技能。v1 仅产出中文简历（LaTeX→PDF）。
license: MIT
---

# CV-Forge

扮演**资深简历制作专家**，根据 JD 从素材库打磨出定制化中文简历（LaTeX→PDF），并附匹配分析与独立评审。

## 核心边界（最重要，动手前必读）

这三条是底线。比起死记命令，更重要的是理解它们背后的道理——想通了 why，遇到模板没覆盖的情形你也能做出对的判断。

1. **真实为主，合理补强** — 简历的价值是帮 HR 认识**真实的你**，而非虚构一个"更好的你"。一旦面试被追问，编造的经历/数字/技能立刻穿帮，反噬候选人。所以只可重排、筛选、按 JD 词汇润色、突出 profile 里**已有**的真实指标；profile 里没有的，绝不凭空写进简历。细则见 `references/tailoring-rules.md`。
2. **关键信息原样保留（verbatim）** — 姓名、公司法定主体、岗位名、起止时间、论文名、项目名都是**客观事实**：HR 会据此核实，ATS 按原词匹配，改写美化只带来风险、毫无收益。因此这些字段一字不差照搬 profile，不归类、不翻译、不"优化"。公司标题可增加经确认或权威来源核实的集团/品牌展示性旁注，但不能替代法定主体；细则见 `references/resume-craft.md` 规则 A1。生成后用 `scripts/check_fidelity.py` 机器兜底校验。
3. **单页纪律** — 校招/实习简历的**页数是硬约束**：目标为 1 页，溢出到第二页必须压缩。填充率只作提示，不作为质量分或交付门槛；内容偏少也不得为了填页添加兴趣、普通奖项、重复 bullet 或无关技术。细则见 resume-craft.md A2。

裁剪改写前请加载 `references/resume-craft.md`（专家写作准则）与 `references/tailoring-rules.md`（真实性硬边界）——它们是本技能"专家水准"的来源，别凭记忆裁剪。

## 路径约定（重要）

- **素材库（长期复用）**：`~/.cv-forge/master-profile.yaml`（全局主目录，跨工作目录复用；首次自动创建）。脚本路径用 `$HOME/.cv-forge/master-profile.yaml`。
- **简历产物（每次投递）**：输出到**用户当前工作目录**下的 `cv-forge/<公司>-<岗位>-<语言>-<日期>/`，方便用户就地查看，不要埋进 skill 安装目录。
- **skill 自身资源**（脚本、模板）：在 skill 安装目录内，用绝对路径或相对 skill 根引用。
- 下文命令里的 `$PROFILE` = `~/.cv-forge/master-profile.yaml`，`$OUT` = `./cv-forge/<公司>-<岗位>-<语言>-<日期>`，`$SKILL` = skill 安装根目录。

## 维护素材库（独立动作，可不接 JD）

当用户要**新增/更新经历**（如「我新做了个项目」「换实习了，更新经历」「这个数字重测了，改一下」「把某段隐藏掉」），或丢来新文档要并入素材库时，按 `references/profile-update.md` 增量更新 `~/.cv-forge/master-profile.yaml`：**合并不覆盖、保持已有 id 不变、新增分配唯一稳定 id、改动后跑 `validate_profile.py`、确认后再写**。这是独立能力，无需先有 JD。

## 工作流（按序执行；细节见 `references/workflow.md`）

### 0. 探测引擎（先做）
```bash
bash scripts/detect_engine.sh
```
若 `available:false`，按输出的安装指引引导用户安装 tectonic（推荐）后**停下等待**。这里不静默降级，是因为 v1 唯一的成品形态是 PDF；没有引擎硬出一个残缺产物，反而会让用户误以为成功。

### 0.5 确定任务模式与岗位族

- **有 JD**：提炼岗位使命与 Top 3 要求，以目标岗位为唯一主线。
- **通用简历**：先从用户指定方向或 profile 证据确定一个岗位族；若用户只说“做一份通用版”且存在多个合理方向，先用一个简短问题确认。Agent / RAG 与搜索 / 推荐等相邻方向必须生成**独立版本**。
- 每个岗位族写入**独立输出目录**，目录名含岗位族或版本后缀；不得覆盖已有 PDF、`tailor.json` 或其他方向的简历。
- Agent / RAG、搜索 / 推荐及广告算法的证据侧重点按 `references/resume-craft.md` §F 执行；没有 CTR/CVR 等证据时不得把搜索推荐版扩大命名为搜广推。
- 岗位族确定后立即 `mkdir -p "$OUT"`，把本次岗位使命、Top 3 能力、ATS 词和来源写入 `$OUT/target-role.json`。有 JD 时记录 JD 来源；通用版标记 `mode=generic` 并记录岗位族，后续匹配和独立评审只读这份冻结画像。

### 1. 接收并解析 JD
JD 可能是粘贴文本 / 网页 URL（用 WebFetch）/ 截图（用视觉读取）。归一为纯文本，确认是中文。按 `references/jd-analysis.md` 先提炼一句话岗位使命和 Top 3 核心要求，再解析其余要求与 ATS 关键词。

若 JD 指向具体公司，在裁剪前按 `references/jd-analysis.md` 核对目标公司与 profile 中当前/过往雇主的**公司别名、关联品牌和集团关系**。发现可能属于同一主体或品牌体系时，必须**主动询问**用户这是回归测试、内部转岗、重复投递还是需要规避的歧义；用户确认测试场景后可继续，不擅自删除经历。

### 2. 加载或构建素材库
- 已有 `$PROFILE`（`~/.cv-forge/master-profile.yaml`）→ 校验：
  ```bash
  python3 "$SKILL/scripts/validate_profile.py" "$PROFILE"
  ```
- 没有 → 先 `mkdir -p ~/.cv-forge`，从用户旧简历抽取（schema 见 `references/profile-schema.md`，可参考 `examples/sample-master-profile.yaml`）：
  ```bash
  python3 "$SKILL/scripts/extract_profile.py" <用户的 resume.tex> -o "$PROFILE"
  ```
  抽取结果是草稿，**请用户确认补充**（尤其 skills / summary）。学到的新事实写回该 YAML。
- 已有库但用户带来新经历/新文档 → 走「维护素材库」（`references/profile-update.md`）增量合并。

### 3. 匹配分析
按 `references/jd-analysis.md`，把每条 JD 要求与 profile 的 skills/tags/metrics 比对，分类为 **覆盖 / 部分 / 缺口**。缺口**绝不编造填补**。

### 3.5 缺口追问访谈（专家关键环节）
若关键证据缺少可核实结果、已有指标缺口径/基线/评测方式，或某 JD 核心要求只是「部分」匹配，按 `references/interview.md` **主动向用户提问**，把确认后的事实写回 `$PROFILE`。不是每条 bullet 都必须有数字；只挖真实信息，绝不替用户编造。

### 4. 专家裁剪 → tailor.json
加载 `references/resume-craft.md`（写作准则 A–G）与 `references/tailoring-rules.md`（真实性边界），按其标准把选中的内容裁剪、重排、润色，产出 `schema_version=2` 的 `tailor.json`（结构见 `references/workflow.md`，可对照 `examples/sample-tailor-jd.json`）。强动词公式、STAR、量化纪律、技术栈过滤、加粗克制、排序原则等细节**一律以 resume-craft.md 为准**，不在此复述。本步只需守住这些 body 级约束：
- **每条进入简历的内容都必须能追溯到 profile 的某个 id**（经 `bullet_ids` / `bullet_overrides`）——这是"不编造"的执行支点。
- 每段 `intro` 必须带同条目的 `intro_source_ids`；每条 `bullet_overrides` 必须带 `override_audit`（来源 id、改写类型、说明）。来源中没有的数字不得进入改写。
- **heading 里的公司/岗位/时间 verbatim**；只在 bullet 描述里用 JD 词汇润色（craft A1）。
- 公司关系先作为经用户确认的 `profile.experience[].org_relations` 事实保存；`tailor.json` 只能用 `org_note_ref` 引用稳定 ID，不能内联实体、关系或证据。显示文案由关系枚举固定生成；「旗下/子公司/母公司」等控制关系只接受权威来源。
- 核心 bullet 默认用“**问题 → 方法 → 结果**”组织，但不机械添加标签；Agent 约束必须保留 Prompt、运行时和会话级策略的真实层级（craft B/E2）。

### 5. 填充模板 + 保真校验 + 编译
产物输出到**当前工作目录**下的 `$OUT`（`./cv-forge/<公司>-<岗位>-<语言>-<日期>`），不要写进 skill 安装目录。
```bash
mkdir -p "$OUT"
# 由 profile + tailor.json 生成 resume.tex
python3 "$SKILL/scripts/fill_template.py" "$PROFILE" "$OUT/tailor.json" \
    -t "$SKILL/assets/templates/zh-classic/resume.tex.tmpl" -o "$OUT/resume.tex"
# 保真检查(硬门槛): 关键信息必须与素材库一字不差; 违规则修正 tailor.json 重来
python3 "$SKILL/scripts/check_fidelity.py" "$PROFILE" "$OUT/tailor.json"
# 在临时目录就位字体并编译, 只把成品 resume.pdf 放回 $OUT(产物目录保持精简)
bash "$SKILL/scripts/build_resume.sh" "$OUT/resume.tex" \
    -t "$SKILL/assets/templates/zh-classic" -o "$OUT"
```
`build_resume.sh` 内部调用 `render_pdf.sh` 探测引擎并编译；字体在临时目录里就位、编译后已嵌进 PDF，所以 `$OUT` 只留 `resume.pdf` / `resume.tex`，不再塞进 ~43MB 字体（避免用户每投一个岗位就多占几十 MB）。用户有照片时给 `build_resume.sh` 传 `--photo <jpg>`（profile `basics.photo: true` 才会显示）。

### 5.5 单页校准（CALIBRATE，机器度量 + 有界，详见 SPEC §11.3/§11.7）
**不要肉眼判断页数。** 用脚本量页数与填充比：
```bash
python3 "$SKILL/scripts/page_metrics.py" "$OUT/resume.pdf" > "$OUT/page_metrics.json"
```
- `pages_int==1` → 页数达标，直接进第 6 步；`pages_int>1` → 只删减弱相关、重复或组件清单化内容，重跑第 5 步重新量页。
- **有界**：为压回 1 页最多调整 2 次（`cal≤2`）；仍超过 1 页则继续进入评审，但最终只能交付 DRAFT，不得用缩到难读的字号规避页数约束。
- `fill_ratio` 只产生 `sparse` / `dense` 提示：偏稀疏不自动补内容，偏拥挤只提示检查可读性。它不触发校准、不参与六维评分、best 选择或 `deliverable` 判定。
- **不得为了填页**添加兴趣、个人特点、普通奖项、重复 bullet 或与 Top 3 核心要求无关的技术；真实证据不足就接受留白并在报告说明。
- `page_metrics.py` 退出码 2（缺 pdfinfo/pdftotext）→ 报告度量不可用，不凭目测宣称页数达标。
- **循环计数落盘**到 `$OUT/polish-state.json`（schema 见 §11.4），由编排层初始化、`polish_gate.py` 改写——"校准/迭代了几次"以状态文件为准，不凭记忆。
- 每次重新编译后都覆盖生成 `$OUT/page_metrics.json`；gate 只读取这份与当前 PDF 同轮生成的度量。
- 机器度量通过后必须做一次**视觉检查**，核对公司标题整体加粗、长公司名与右侧日期留有间距、无重叠/截断、论文标题换行和底部留白可读。必须保存首页预览，把当前 PDF 的 SHA-256、预览路径和固定检查字段写入 `$OUT/layout-check.json`（schema 见 workflow），一并传给 Reviewer；视觉检查不能替代 `pages_int` 的机器页数判断。

### 6. 独立子 agent 评审 + 三态裁决 + 匹配报告（不可自评，循环由 SPEC §11 终止）
```bash
python3 "$SKILL/scripts/ats_check.py" <jd.txt> "$OUT/resume.pdf"
pdftotext "$OUT/resume.pdf" "$OUT/resume.txt"   # 给评审子 agent 的输入
```
质量评判由**独立子 agent**完成，生成 agent 不得自评——自评会系统性偏高（看不到自己的盲点、偏袒自己的措辞）。按 `references/review-agent.md`：
- spawn **评审员**子 agent：只拿 `$OUT/target-role.json` + 渲染后简历纯文本 + `references/review-rubric.md`、`references/resume-craft.md`、`references/tailoring-rules.md` + `$OUT/layout-check.json`/首页预览，按六维度打分（满分 30）+ 改进点；每条改进**自带 `category`(`actionable`/`needs-fact`)/`axis` 字段**，落盘 `$OUT/reviewer.json`。
- spawn **对抗挑错员**子 agent：在上述输入外，可对照 master profile、`tailor.json` 的 source audit 与 `org_note_ref` 核查虚报、指标口径、公司关系、Demo 包装、组件清单、ownership 与不可追溯问题；每条 red_flag 同样自带 `category`/`severity` 字段，落盘 `$OUT/critic.json`。
- **停不停、交付哪一版由脚本机器裁决**（不再凭散文判断）：
  ```bash
  python3 "$SKILL/scripts/polish_gate.py" --state "$OUT/polish-state.json" \
      --metrics "$OUT/page_metrics.json" --review "$OUT/reviewer.json" \
      --critic "$OUT/critic.json" --target-pages 1
  ```
  按退出码分支：**10 = revise** → 仅依 `actionable` 发现修订 tailor.json（守真实性边界，缺数字只能追问不可编造）→ 重跑第 5 步（`MAX_ROUNDS=1` 封顶，至多一轮）；修订版完成后必须重做 metrics、视觉检查，并从新的 `resume.txt` **重新生成** `reviewer.json` 和 `critic.json` 再调用 gate，**不得复用上一轮**评审。**0 = 终止** → `pass`/`deliver-best` 都进交付态。**2 = 输入缺失/异常** → 不自由重试；按 SPEC §11 的失败出口处理并保留 DRAFT/审计。
- **关键反死循环规则（§11.6/§11.8）**：只有 `actionable` 发现触发迭代；全是 `needs-fact`（缺真实数字、JD 缺口）则 `actionable_count==0` → 直接 `deliver-best`，**不消耗轮次**，改走 `interview.md` 追问或写进缺口段。`deliverable==false` 时产物命名 `resume.DRAFT.pdf` + 报告顶部加 `NOT-READY` 横幅，**绝不为达标编造**。
- **无子 agent 能力的环境**（如部分 IDE 集成）：至少在一次**全新、干净的上下文**里、仅喂 JD + 纯文本 + rubric 做一次评审，并在报告里标注评审方式。评审 spawn 失败/返回非法 JSON 时 `polish_gate.py` 按 `review_unavailable` 单向交付、不重试。

gate 退出码为 0 后，必须用终止 state 完成命名并落盘机器摘要：
```bash
python3 "$SKILL/scripts/finalize_delivery.py" --state "$OUT/polish-state.json" \
    --pdf "$OUT/resume.pdf" --out-dir "$OUT" > "$OUT/delivery-summary.json"
```
只有 state 已终止、`deliverable=true`、`selected` 无 high flag，且 `last_review_round==round` 时才保留正式 `resume.pdf`；其余情况统一改名为 `resume.DRAFT.pdf`。`selected` 对应刚评审且实际存在的 PDF，历史 `best` 只用于轮次比较。`decision=revise` 时即使误调用 finalizer，也绝不能产生正式版。

把 `delivery-summary.json` 中的 `decision`、`deliverable`、`delivery_reason`、`score`、`high_flags` 与文件名原样写入 `$OUT/match-report.md`，不要自行重算门槛或手写分数不等式；`polish-state.json` 一并留在 `$OUT` 作"为何在此停下"的审计（§11.11）。

## 产物

每次运行输出到**当前工作目录**下的 `cv-forge/<公司>-<岗位>-<语言>-<日期>/`：
- `resume.pdf` — 仅在 finalizer 确认可投递时存在的正式简历
- `resume.DRAFT.pdf` — 未达门槛或尚未终止时的草稿（与正式版互斥）
- `resume.tex` — 可手改的源文件（重新出 PDF 时再跑一次 `build_resume.sh` 即可自动铺字体编译）
- `tailor.json` — 裁剪审计（每条内容的来源 id）
- `target-role.json` — 冻结的 JD / 通用岗位画像与 Top 3 能力
- `page_metrics.json` / `layout-check.json` — 当前 PDF 的机器页指标与视觉检查记录
- `match-report.md` — JD 匹配分析报告
- `delivery-summary.json` — 从终止 gate state 生成的交付摘要，供报告原样引用

## 范围（v1）

仅中文、仅 LaTeX→PDF、内置 zh-classic 模板。英文/双语、飞书/docx/HTML、自定义/网络模板见 SPEC.md 的后续迭代。若用户拿来英文 JD 或想要英文简历，说明 v1 暂只产出中文简历，请其确认后再继续。

## 隐私

- 素材库 `~/.cv-forge/master-profile.yaml` 与产物 `cv-forge/` 都含个人隐私（姓名/电话/邮箱/照片）。
- 它们在用户机器本地，**绝不提交进 skill 仓库**；建议用户在自己的工作目录用 `.gitignore` 忽略 `cv-forge/`。
- skill 仓库自带的 `.gitignore` 已排除 `cv-forge/`、`output/`、`data/master-profile.*`。
