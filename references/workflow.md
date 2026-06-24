# 完整工作流（展开）

本文件展开 SKILL.md 的工作流，给出每步的细节、数据结构与边界处理。

## 状态机总览

```
[0 探测引擎] → [1 解析 JD] → [2 加载/建素材库] → [3 匹配分析]
   → [4 裁剪 tailor.json] → [5 填模板+编译 PDF] → [6 匹配报告]
```

## 0. 探测引擎

`bash scripts/detect_engine.sh` 输出 JSON。`available:false` 时按 OS 给安装指引并停下：
- macOS: `brew install tectonic`
- Debian/Ubuntu: `apt install texlive-xetex`（或 tectonic release）
- Windows: `winget install tectonic` / `scoop install tectonic`

不在缺引擎时静默降级（v1 唯一输出路径是 LaTeX→PDF）。

## 1. 解析 JD

输入三种形态：
- **粘贴文本**：直接用。
- **URL**：用 WebFetch 抓取，提取正文 JD。
- **截图 / PDF**：截图用视觉直接读取（v1 不假设系统装了 OCR 命令）；PDF 可用 pdftotext。

归一为纯文本后，确认语言为中文（v1）。按 `jd-analysis.md` 结构化。

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
  "company": "公司名",
  "role": "岗位名",
  "sections": [
    {
      "title": "实习经历",
      "entries": [
        {
          "ref": "expe-rag",
          "heading": "\\textbf{Agent 工程师} \\hfill \\textbf{某科技有限公司}",
          "date": "2025.01 - 2026.01",
          "bullet_ids": ["expe-rag-b1", "expe-rag-b3"],
          "bullet_overrides": {
            "expe-rag-b1": "（按 JD 措辞润色后的文案，语义不变）"
          }
        }
      ]
    }
  ]
}
```

规则：
- `bullet_ids` 只能引用 profile 中真实存在的 bullet id。
- `bullet_overrides` 是对**已有** bullet 的措辞润色，不得引入新事实/新数字。
- `heading` / `date` 是已排版的 LaTeX 片段（`fill_template.py` 中按 raw 字段不转义）。
- 章节顺序、条目顺序 = 按 JD 相关性重排的结果。

> **提示**：为了让 ATS 命中率更高，技术栈 bullet（含 Python/FastAPI/向量库等关键词）通常应保留——它们是关键词的主要载体。裁剪时别把含关键词的真实 bullet 误删。

## 5. 填模板 + 编译

路径约定（见 SKILL.md）：`$PROFILE`=`~/.cv-forge/master-profile.yaml`，`$OUT`=当前工作目录下的 `./cv-forge/<公司>-<岗位>-<语言>-<日期>`，`$SKILL`=skill 安装根目录。

```bash
mkdir -p "$OUT"
cp -R "$SKILL/assets/templates/zh-classic/." "$OUT/"   # 字体/cls/sty 就位(相对路径)
python3 "$SKILL/scripts/fill_template.py" "$PROFILE" "$OUT/tailor.json" \
    -t "$SKILL/assets/templates/zh-classic/resume.tex.tmpl" -o "$OUT/resume.tex"
bash "$SKILL/scripts/render_pdf.sh" "$OUT/resume.tex" -o "$OUT"
```

照片：profile `basics.photo` 为 true 时模板会引用 `images/`，需确保 `$OUT/images/` 下有照片（默认带 placeholder.jpg；用户可替换为自己的）。

## 6. 匹配报告

```bash
python3 "$SKILL/scripts/ats_check.py" <jd.txt> "$OUT/resume.pdf"
```

把命中表与覆盖表、缺口清单、补强审计合并写入 `$OUT/match-report.md`。

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
- 缺口（未编造）：<JD 要求 X> 在 profile 中无证据，未写入
```

## 失败与回退

- 编译失败：`render_pdf.sh` 返回非 0，读其 stderr 定位（常见：照片路径、特殊字符）。
- 引擎缺失：返回 3 并给安装指引，停下等用户。
- profile 校验失败：先修 `~/.cv-forge/master-profile.yaml` 再继续。
