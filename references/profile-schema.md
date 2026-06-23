# Master Profile Schema（素材库格式）

`master-profile.yaml` 是你的个人素材**单一真相源**：一次建好，之后每次按 JD 从中筛选裁剪。
本文件定义其结构。v1 仅中文，字段值为普通字符串。

## 顶层结构

```yaml
schema_version: 1
meta:
  lang: zh                  # v1 固定 zh
  updated: 2026-06-23       # 最后更新日期（字符串）

basics:                     # 必填
  name: 李明                # 必填
  phone: "138-0000-0000"    # 必填（字符串，保留前导/分隔符）
  email: liming@example.com # 必填
  photo: true               # 可选，是否在简历显示照片，默认 false
  photo_size: 0.12          # 可选，照片宽度占纸宽比例
  headline: 后端/Agent 工程师   # 可选，一句话定位

summary: |                  # 可选，自我评价/总结（最常被按 JD 改写的自由文本）
  ...

skills:                     # 可选但强烈建议；用于 JD 匹配
  - group: 编程语言         # 技能分组名
    items:
      - name: Python
        level: proficient   # 可选: exposure|familiar|proficient|expert
        years: 4            # 可选
        evidence_refs: [exp-acme]   # 可选，软提醒：指向证明它的条目 id
      - name: Go
  - group: 框架与工具
    items:
      - name: LangChain
        evidence_refs: [exp-acme, proj-course-agent]

experience:                 # 实习/工作经历
  - id: exp-acme           # 必填，稳定 id（裁剪只引用、不新增）
    org: 某科技有限公司   # 必填，单位
    title: Agent 工程师       # 必填，职位
    date: "2025.01 - 2026.01" # 必填，时间段（字符串，保留原格式）
    tech: [LangChain, FastAPI, FAISS]   # 可选，技术栈
    tags: [RAG, 检索, 微调]   # 可选，语义标签，用于 JD 匹配
    bullets:
      - id: exp-acme-b1     # 必填，稳定 id
        text: 构建端到端旅行套餐生成系统……   # 必填，要点文本（纯文本，自动 LaTeX 转义）
        metrics:             # 可选，结构化真实指标（补强=复用这些数字，不可编造）
          latency_s: 42
        tags: [RAG, 系统设计]

projects:                   # 项目经历，结构同 experience
  - id: proj-course-agent
    name: 多Agent选课推荐系统   # 项目名（projects 用 name 而非 org/title）
    role: 独立项目            # 可选
    date: ""                 # 可选
    url: https://github.com/example/course-recommend-agent  # 可选
    tech: [FastAPI, LangGraph, Milvus]
    tags: [Multi-Agent, RAG]
    bullets:
      - id: proj-course-agent-b1
        text: ...

research:                   # 科研/论文，结构同上
  - id: pub-cvpr-1
    name: "Boosting the dual-stream architecture ..."   # 论文标题
    venue: CVPR2025 (CCF-A)  # 可选，发表处
    role: 共同一作            # 可选
    date: ""
    bullets:
      - id: pub-cvpr-1-b1
        text: 提出了分辨率偏置的不确定性估计……

education:                  # 教育经历
  - id: edu-grad          # 必填，稳定 id
    school: 某重点大学（985）   # 必填
    degree: 硕士（保研）       # 可选
    field: 计算机技术          # 可选
    date: "2024.09 - 2027.06" # 必填
    bullets:                 # 可选（导师、荣誉等）
      - id: edu-grad-b1
        text: "导师：……"

awards: []                  # 可选，独立奖项（也可并入 education bullets）

preferences:                # 可选，不打印，仅指导裁剪
  target_titles: [后端工程师, Agent 工程师]
  max_pages: 1
  exclude_ids: []           # 永不出现在简历里的 id
```

## 校验规则（`validate_profile.py`）

**硬性（缺失即报错，退出码非 0）：**
- 顶层含 `basics`；`basics.name` / `basics.phone` / `basics.email` 三者非空。
- `experience` / `projects` / `research` / `education` 若存在，必须是列表；每个条目含**非空 `id`**。
- 同类下 `id` 唯一；所有 bullet 的 `id` 在全局唯一。
- 经历类条目含必填定位字段：`experience` 需 `org`+`date`（`title` 推荐）；`projects`/`research` 需 `name`；`education` 需 `school`+`date`。

**软提醒（不报错，仅列出 warning）：**
- 某 `skills.items[].name` 没有 `evidence_refs` → 提醒"此技能未关联证据，请确认属实"。
- `evidence_refs` 指向了不存在的 id → 提醒悬空引用。
- 缺 `summary` / `skills` → 提醒补充以提升匹配质量。

## 设计意图

- **稳定 id 是裁剪的支点**：按 JD 定制 = 选择/重排/润色这些 id 对应的内容，**绝不新增 id**。
- **`metrics` 结构化**：把真实数字单独存，"合理补强"= 把已有真实数字前置/突出，而非编造新数字。
- **`evidence_refs` 软约束**：技能的可信度可追溯；缺了不阻断，但会在匹配报告里标注，把判断权交回用户。
