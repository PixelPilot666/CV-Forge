# 完整工作流（展开）

本文件展开 SKILL.md 的工作流，给出每步的细节、数据结构与边界处理。

## 状态机总览

```
[0 探测引擎] → [0.5 确定模式/岗位族] → [1 解析 JD/通用岗位画像] → [2 加载/建素材库] → [3 匹配分析]
   → [4 裁剪 tailor.json] → [5 填模板+保真+编译] → [5.5 页指标+视觉检查]
   → [6 独立评审] → [7 polish_gate 三态裁决]
       ├─ exit 10 / revise → [有界修订一次] → 回到 [5]
       ├─ exit 0 / pass|deliver-best → [8 finalizer + 匹配报告] → DELIVER
       └─ exit 2 / 输入缺失或异常 → [失败出口，保留 DRAFT 与审计] → DELIVER
```

## 0. 探测引擎

`bash scripts/detect_engine.sh` 输出 JSON。`available:false` 时按 OS 给安装指引并停下：
- macOS: `brew install tectonic`
- Debian/Ubuntu: `apt install texlive-xetex`（或 tectonic release）
- Windows: `winget install tectonic` / `scoop install tectonic`

不在缺引擎时静默降级（v1 唯一输出路径是 LaTeX→PDF）。

## 0.5 确定模式与岗位族

- 有 JD 时，以目标岗位使命与 Top 3 要求为主线。
- 无 JD 的通用简历以一个岗位族为主线；Agent / RAG、搜索 / 推荐等方向分别生成，不把互相竞争的证据平均塞进同一份简历。
- 多版本共用 master profile，但必须写入独立输出目录；已有版本不覆盖，便于用户比较和回归。
- 岗位族确定后立即创建 `$OUT`，再写冻结画像；不要等到编译阶段才创建目录。

## 1. 解析 JD 或通用岗位画像

输入三种形态：
- **粘贴文本**：直接用。
- **URL**：用 WebFetch 抓取，提取正文 JD。
- **截图 / PDF**：截图用视觉直接读取（v1 不假设系统装了 OCR 命令）；PDF 可用 pdftotext。

归一为纯文本后，确认语言为中文（v1）。按 `jd-analysis.md` 结构化。

无 JD 时，用 `resume-craft.md` §F 的岗位族侧重点构造一份简短“通用岗位画像”，至少包含岗位使命、Top 3 能力和 ATS 核心词；后续匹配、评审仍使用该画像，不因“通用”而省略岗位主线。

将画像冻结为 `$OUT/target-role.json`，避免写作、评审各自理解一套目标：

```json
{
  "mode": "jd",
  "role_family": "Agent/RAG",
  "mission": "围绕工具调用、RAG 与评测交付可控 Agent 应用",
  "top_requirements": ["Agent 工作流", "RAG 检索", "评测与可观测性"],
  "ats_keywords": ["Python", "Tool Calling", "RAG", "Evaluation"],
  "source": {"type": "jd_text", "reference": "jd.txt"}
}
```

通用版使用 `mode=generic`，`source.reference` 记录“用户指定岗位族”或 profile 证据摘要；同一轮中不得修改这份画像来迁就已生成的简历。

## 2. 加载 / 构建素材库

- 有 `~/.cv-forge/master-profile.yaml` → `validate_profile.py` 校验；按软提醒补全。
- 无 → `extract_profile.py <resume.tex>` 抽取草稿 → **让用户确认补充**（skills/summary/metrics 往往需要手动补）。
- 任何对话中新得到的真实事实，写回 YAML（经用户确认），让素材库越用越完整。

## 3. 匹配分析

见 `jd-analysis.md`。产出覆盖 / 部分 / 缺口三类，缺口绝不编造。

## 4. 裁剪：tailor.json 结构

LLM 依据匹配结果产出 `tailor.json`。这是裁剪的唯一载体，也是审计依据：

```json
{
  "schema_version": 2,
  "company": "公司名",
  "role": "岗位名",
  "sections": [
    {
      "title": "实习经历",
      "entries": [
        {
          "ref": "expe-rag",
          "heading": "\\textbf{Agent 工程师} \\hfill \\textbf{某科技有限公司（某集团旗下）}",
          "date": "2025.01 - 2026.01",
          "org_note_ref": "expe-rag-rel-group",
          "intro": "负责 Agent 检索与评测链路。",
          "intro_source_ids": ["expe-rag", "expe-rag-b1"],
          "bullet_ids": ["expe-rag-b1", "expe-rag-b3"],
          "bullet_overrides": {
            "expe-rag-b1": "（按 JD 措辞润色后的文案，语义不变）"
          },
          "override_audit": {
            "expe-rag-b1": {
              "source_ids": ["expe-rag-b1"],
              "change_type": "reframe",
              "claim_notes": "只调整为问题—方法—结果顺序，未新增事实或数字"
            }
          }
        }
      ]
    }
  ]
}
```

规则：
- `bullet_ids` 只能引用 profile 中真实存在的 bullet id。
- `intro_source_ids` 只能引用当前 profile 条目本身或其 bullet；有 `intro` 就必须填写。
- 每个 `bullet_overrides` 都必须有同 key 的 `override_audit`。`source_ids` 只允许当前条目的 bullet，`change_type` 取 `reframe` / `compress` / `merge`；不得引入来源里没有的新事实/新数字，不得改换数字单位、数量级或调换基线与结果顺序。
- `heading` / `date` 是已排版的 LaTeX 片段（`fill_template.py` 中按 raw 字段不转义）。
- 章节顺序、条目顺序 = 按 JD 相关性重排的结果。
- company heading 必须完整包含 profile 的法定主体。集团/品牌关系先按 `profile-schema.md` 写入当前经历的 `org_relations`，经用户确认并由 `validate_profile.py` 校验；tailor 只写同条目的 `org_note_ref`，禁止内联 `org_note`，也不能直接拼 raw heading 绕过审计。显示文案由 profile 中的关系枚举固定生成：`group_affiliate → {entity}旗下`、`subsidiary → {entity}子公司`、`parent_company → 母公司：{entity}`、`brand → 品牌：{entity}`、`product → 产品：{entity}`。旁注与法定主体整体加粗，不写回 `org`，也不在简介重复。
- 核心 bullet 按“问题 → 方法 → 结果”组织；Prompt 约束、运行时限制和会话级策略分层写清。

> **提示**：为了让 ATS 命中率更高，技术栈 bullet（含 Python/FastAPI/向量库等关键词）通常应保留——它们是关键词的主要载体。裁剪时别把含关键词的真实 bullet 误删。

## 5. 填模板 + 编译

路径约定（见 SKILL.md）：`$PROFILE`=`~/.cv-forge/master-profile.yaml`，`$OUT`=当前工作目录下的 `./cv-forge/<公司>-<岗位>-<语言>-<日期>`，`$SKILL`=skill 安装根目录。

```bash
mkdir -p "$OUT"
python3 "$SKILL/scripts/fill_template.py" "$PROFILE" "$OUT/tailor.json" \
    -t "$SKILL/assets/templates/zh-classic/resume.tex.tmpl" -o "$OUT/resume.tex"
python3 "$SKILL/scripts/check_fidelity.py" "$PROFILE" "$OUT/tailor.json"   # 硬门槛
bash "$SKILL/scripts/build_resume.sh" "$OUT/resume.tex" \
    -t "$SKILL/assets/templates/zh-classic" -o "$OUT"
```

`build_resume.sh` 在**临时目录**里就位模板资源(fonts/cls/sty/images) + tex，调用 `render_pdf.sh` 用相对路径编译，再只把成品 `resume.pdf` 放回 `$OUT`。这样产物目录保持精简（pdf + tex），不再每次复制 ~43MB 中文字体；字体已嵌入 PDF，成品可直接投递。需要重新出 PDF 时（手改了 resume.tex），再跑一次本脚本即可重新铺字体编译。

照片：profile `basics.photo` 为 true 时模板会引用 `images/you.jpg`。把用户照片传给 `build_resume.sh --photo <jpg>`；没传则用模板自带的 `placeholder.jpg`（中性剪影）兜底，保证仍能编译。`photo: false` 时模板不引用照片，无需操心。

每次编译后落盘机器指标：

```bash
python3 "$SKILL/scripts/page_metrics.py" "$OUT/resume.pdf" > "$OUT/page_metrics.json"
```

再渲染首页预览做视觉检查：公司名/集团旁注是否整体加粗，长公司名与日期是否重叠，正文和论文标题是否截断，底部是否有异常大块空白。视觉检查只判断排版，不替代机器页数。结果固定写入 `$OUT/layout-check.json`：

```json
{
  "page": 1,
  "pdf_sha256": "<当前 resume.pdf 的 SHA-256>",
  "preview_path": "resume-page-1.png",
  "checked_by": "independent_reviewer",
  "company_date_overlap": false,
  "text_clipped": false,
  "heading_bold_consistent": true,
  "paper_title_readable": true,
  "large_blank_area": false,
  "notes": []
}
```

修订后必须覆盖 `page_metrics.json`、`layout-check.json` 和首页预览，使它们与当前 `resume.pdf` 同轮；Reviewer 核对 `pdf_sha256` 后再采用视觉结论。

## 6. ATS 检查与独立评审

```bash
python3 "$SKILL/scripts/ats_check.py" <jd.txt> "$OUT/resume.pdf"
pdftotext "$OUT/resume.pdf" "$OUT/resume.txt"
```

按 `review-agent.md` 生成 `$OUT/reviewer.json` 和 `$OUT/critic.json`。Reviewer 只读 `target-role.json`、`resume.txt`、rubric 与 layout audit/首页预览；Critic 可额外读取 master profile、`tailor.json` 的来源审计，检查超出素材和指标口径。生成 agent 不自评。

## 7. 三态裁决与唯一终止路径

```bash
python3 "$SKILL/scripts/polish_gate.py" --state "$OUT/polish-state.json" \
  --metrics "$OUT/page_metrics.json" --review "$OUT/reviewer.json" \
  --critic "$OUT/critic.json" --target-pages 1
```

- `10 = revise`：只修 `actionable`；至多一轮。重跑填充、保真、编译、metrics、视觉检查，并基于新 PDF 重新生成两份评审，不能复用旧 JSON。
- `0 = 终止`：读取 stdout/state 的 `decision`；`pass` 与 `deliver-best` 都进入 finalizer。
- `2 = 输入缺失/异常`：不进入自由重试循环；按 SPEC §11 的失败出口终止，并保留 DRAFT 与错误审计。
- 未解决的 high 虚报/夸大项必须先**删除或降级**；若仍存在 high flag，该版本不得进入正式 PDF。需要未来补证的内容另记为 `needs-fact`，不能让可疑表述暂留正文。

## 8. Finalizer 与匹配报告

gate 终止后运行：

```bash
python3 "$SKILL/scripts/finalize_delivery.py" --state "$OUT/polish-state.json" \
  --pdf "$OUT/resume.pdf" --out-dir "$OUT" > "$OUT/delivery-summary.json"
```

`deliverable=true` 才保留 `resume.pdf`；否则只交付 `resume.DRAFT.pdf`。把 ATS 命中表、覆盖/缺口、补强审计、独立评审、未修复项，以及 `delivery-summary.json` 的机器字段合并写入 `$OUT/match-report.md`。

### match-report.md 模板

```markdown
# JD 匹配报告 — <岗位>

## 岗位概览
- JD 语言：中文
- 硬性要求 N 条 / 加分项 M 条

## 覆盖表
| JD 要求 | 状态 | 证据(profile id) |
|---|---|---|
| 精通 Python | 覆盖 | expe-rag, proj-course-agent |
| ... | 部分/缺口 | ... |

## ATS 关键词命中
（ats_check.py 输出的表）

## 缺口清单
- <未覆盖要求>：建议补充？(向用户提问)

## 补强审计
- 强调/重排：把 expe-rag 置顶（与 JD 的 RAG 要求最相关）
- 措辞润色：expe-rag-b2「混合召回」→ 表述为「向量检索+关键词检索」(语义不变)
- 来源审计：intro 与 override 的 source ids、改写类型、完整指标口径
- 缺口（未编造）：<JD 要求 X> 在 profile 中无证据，未写入

## 独立评审与交付
- decision / deliverable / delivery_reason：从 delivery-summary.json 原样抄录
- 未修复 actionable / needs-fact / red flags：逐条记录
```

## 失败与回退

- 编译失败：`render_pdf.sh` 返回非 0，读其 stderr 定位（常见：照片路径、特殊字符）。
- 引擎缺失：返回 3 并给安装指引，停下等用户。
- profile 校验失败：先修 `~/.cv-forge/master-profile.yaml` 再继续。
- gate 输入缺失/非法：按 exit 2 的失败出口交付 DRAFT，不在编排层无限重试。
