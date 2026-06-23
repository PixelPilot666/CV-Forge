# 模板与占位符约定

本文件描述 jd-resume 模板的占位符语法，供 `fill_template.py` 填充，也供贡献者新增模板时遵循。

## 占位符语法（跨格式统一）

| 语法 | 含义 | 示例 |
|---|---|---|
| `{{key}}` | 标量替换（已按语言解析为字符串） | `{{name}}` → `李明` |
| `{{#list}} … {{/list}}` | 列表循环，块内对每个元素渲染一次 | `{{#bullets}}\item {{text}}{{/bullets}}` |
| `{{#if key}} … {{/if}}` | 条件块，key 为真值时保留，否则整块删除 | `{{#if photo}}\yourphoto{...}{{/if}}` |

- 循环块内可用元素自身的字段（如 `{{text}}`、`{{heading}}`）。
- 嵌套循环按层级解析：`sections` → 每个 section 的 `entries` → 每个 entry 的 `bullets`。

## LaTeX 转义（关键，集中在脚本里）

填充进 `.tex` 模板的**数据值**会被自动转义以下 LaTeX 特殊字符，避免编译失败或排版错乱：

```
\  →  \textbackslash{}
&  →  \&        %  →  \%        $  →  \$
#  →  \#        _  →  \_        {  →  \{        }  →  \}
~  →  \textasciitilde{}         ^  →  \textasciicircum{}
```

> **转义只作用于"数据值"，不作用于模板骨架。** 模板里本就存在的 `\section{}`、`\textbf{}` 等命令不受影响。
> 例外：素材库里若有意写入的 LaTeX 标记（如 `\href{}`、`\textbf{}`）需要在 schema 中以"富文本/已转义"约定标注；v1 默认把 bullet 文本当纯文本转义，链接通过专门字段处理（见 profile-schema.md）。

## zh-classic 模板的结构映射

`assets/templates/zh-classic/resume.tex.tmpl` 暴露的占位符：

| 占位符 | 来源（master profile） |
|---|---|
| `{{name}}` | `basics.name` |
| `{{phone}}` `{{email}}` | `basics.phone` / `basics.email` |
| `{{#if photo}}` `{{photo_size}}` | `basics.photo`（布尔）/ `basics.photo_size` |
| `{{#sections}}` | 由裁剪结果 `tailor.json` 决定的章节顺序与内容 |
| └ `{{title}}` | 章节名（教育经历 / 实习经历 / 项目经历 / 科研经历…） |
| └ `{{#entries}}` `{{heading}}` `{{date}}` | 每个条目的标题（含 `\textbf`/`\hfill` 排版）与日期 |
| └ └ `{{#bullets}}` `{{text}}` | 每条要点文本 |

`heading` 与 `date` 是已经组好版的 LaTeX 片段（由编排层按模板风格拼装，如 `\textbf{公司} \hfill \textbf{职位}`），因此这两个字段按"已格式化"处理、不整体转义；要点 `text` 默认按纯文本转义。详见 `fill_template.py` 的字段白名单。

## 新增模板

见 CONTRIBUTING.md。每个模板目录需含 `template.json` 与一个 `*.tmpl` 入口文件，字体内置走相对路径。
