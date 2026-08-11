# 已归档实施计划 — SPEC §11「打磨循环与终止保证」

> 本计划已完成并由 CV-Forge v2 方案取代；保留用于历史审计。

## Context（为什么做这件事）

CV-Forge 当前会陷入死循环：SKILL.md §5.5「整页校准」(「重跑第 5 步直到接近整页且铺满」) 和 §6「评审迭代」两个无机器上限的循环相互嵌套，叠加三条互相打架的硬约束（整页铺满 / 真实性边界不准编造 / 评审 total≥26 且无 high red_flag）。素材本就不足时，简历铺不满、评分上不去、又不准编造 → agent「改也改不好、停也不让停」。

SPEC.md 已新增 §11（lines 184–438），把两个循环合并为**唯一一个有界状态机**，所有「停/不停、停在哪版」的判断都改为可由 `pdfinfo` 页数 / 评审 JSON / 状态文件 / 退出码机器判定。**本计划把 §11 从规格落地为可运行实现**，让死循环在实际编排中被根治。

**意图结果**：任意 JD × 任意 profile（含素材严重不足）下，打磨循环都在有限步内必然进入唯一交付态；素材不足时走 best 兜底交付 + 缺口如实标注，而非无限重试。

**两项已敲定决策**：
1. **范围 = 全量 §11**：两个新脚本 + 测试 + 编排文档改写（SKILL.md §5.5/§6、review-agent.md schema、review-rubric.md、SPEC §2 命令表）。脚本本身不改变 agent 行为，必须由 SKILL.md 调用才真正闭环。
2. **fill_ratio = 整数优先、估算为可降级增强**：先交付「保证正确」的整数页数核心（`pdfinfo` 取页数，缺工具退出 2 → §11.3 整数退化路径），bbox `fill_ratio` 作为受同一降级开关保护、由校准检查点放行的精度增强。循环即使 fill_ratio 暂缺也完全可用。

---

## 现状与复用点（探索已确认）

| 约定 | 事实（来源） | 落地动作 |
|---|---|---|
| 退出码 | Python: 0=成功 / 1=检查失败 / 2=输入缺失；shell: 另有 3=无引擎（`build_resume.sh:11`、`check_fidelity.py:9`）| 新脚本沿用；polish_gate 额外用 **10=revise** |
| PDF 取文本 | `ats_check.py:60-84` 已用 `subprocess.run(["pdftotext","-layout",path,"-"], capture_output=True, text=True)` + `_has(cmd)`（`shutil.which`）降级 | page_metrics 复刻该 `_has`/subprocess/缺工具给安装提示模式 |
| 依赖 | stdlib 优先；唯一第三方 PyYAML 经 `_deps.load_yaml` 自愈（`_deps.py`）。两个新脚本**只用 stdlib `json`**，无需 _deps | 不引入新依赖 |
| 脚本骨架 | `#!/usr/bin/env python3`、`main(argv=None)`、`sys.exit(main())`、argparse、结果 JSON 打 stdout、诊断打 stderr（✅/❌/⚠️）、`encoding="utf-8"`、644 不可执行 | 照抄 `check_fidelity.py` 骨架 |
| 测试 | **unittest（非 pytest）**，`python3 -m unittest discover -s tests`；Python 脚本**直接 import** 调函数、shell 用 subprocess；缺工具用 `@unittest.skipUnless(shutil.which(...))` 跳过（`test_e2e_smoke.py:28-29,76`）；CI 不装 tectonic/poppler；`tests/fixtures/` 当前空 | 新测试同构；risky 解析逻辑用「抓取的 pdfinfo/pdftotext 文本片段当 fixture 字符串」做纯函数测试，保持 CI 无工具可跑 |

---

## 依赖图

```
SPEC.md §11（权威契约，只读参照；§2 表 + §11.10 须与脚本实际 CLI/退出码一致）
   │
   ├── Slice 1: polish_gate.py（纯决策引擎）+ test     ← 纯逻辑、零外部工具、载重核心
   │        │ 消费 metrics JSON（数据契约，非调用边）
   │        │ 读 reviewer/critic JSON 的 category 字段 → 依赖 Slice 3 的 schema
   │
   ├── Slice 2: page_metrics.py（2a 整数核心 → 2b fill_ratio 增强）+ test
   │        │ 产出 {pages_int,fill_ratio,pages_float} ← Slice 1 的输入契约
   │
   ├── Slice 3: review-agent.md / review-rubric.md schema 改写（category/axis）+ 契约 test
   │        │ 必须先于 Slice 4 的真实 REVIEW spawn
   │
   └── Slice 4: 编排闭环 — SKILL.md §5.5/§6 → §11 有界循环 + SPEC §2 表 + e2e wiring test
            依赖 Slice 1,2,3 全部落地
```

**关键事实**：`polish_gate.py` 与 `page_metrics.py` **互不调用**，只靠 metrics JSON 形状耦合 → 可任意顺序构建、各自独立单测。`polish_gate.py` 的 `actionable_count` 读 reviewer/critic 的 `category` 字段 → 逻辑可先用手写 fixture 单测，但真实 spawn 前 Slice 3 必须落地。状态文件 `polish-state.json` 由**编排层(agent)** 首次初始化（`round=0,cal=0,*_fix=0,last_dir=none,best=null`），`polish_gate.py` 原子改写（temp+`os.replace`）；gate 须容忍文件缺失（按 §11.4 默认初始化）与已存在两种情况。

---

## 垂直切片（按 风险×价值 排序，高者先行）

### Slice 1 — `polish_gate.py` 纯决策引擎 + 测试 + SPEC §11.10 校验
**最先做**：价值最高（它**就是**终止保证），风险最低（纯确定性逻辑），且在 fill_ratio 还不可信时就能配合整数路径端到端工作。

**改动文件**：`scripts/polish_gate.py`(新)、`tests/test_polish_gate.py`(新)、`tests/fixtures/*.json`(新：reviewer_pass / reviewer_actionable / reviewer_needsfact / critic_clean / critic_high_flag / metrics_inband / metrics_oob / polish_state_init)、`SPEC.md`(仅当 CLI 签名与 §2/§11.10 漂移才改)。

**实现要点**（§11.5–§11.9 逐条转写）：
- 模块级常量：`MAX_ROUNDS=1, CAL_MAX=2, FIDELITY_MAX=2, BUILD_RETRY_MAX=1, PAGE_LO=0.90, PAGE_HI=1.00, DELIVER_SCORE=26, SOFT_FLOOR=24, EPS=0.02`。
- argparse：`--state --metrics --review --critic --target-pages`。
- `in_band(fr,N)`：N==1 → `0.90≤fr≤1.00`；N>1 → `N-0.10≤fr≤N`（绝对平移，§11.3 规则3）。
- `actionable_count`：数 `category=="actionable"`；**兜底强制分类**（§11.6）——`severity=="high"` 且属虚报/夸大/超出素材/技术栈违规 → 强制 actionable；`needs_new_fact==true` 或命中缺数字/无证据/规模/JD缺口关键词 → 强制 needs-fact（防生成 agent 自报标签作弊）。
- `strictly_better(cand,best)`（§11.7 字典序）：① high_flags 更少胜 ② in_band 真胜（硬闸，例外：候选消除 high red_flag 才可越界覆盖带内 best）③ total 高胜 ④ `|fr-带内中点|` 更小且差>EPS，否则并列不覆盖。另含「red_flag 减少即使 total 偶低 1~2 分仍判更优」。
- **算子顺序**：先用「候选 vs 旧 best」判 revise，再在 REVISE 路径更新 best 快照（否则 MAX_ROUNDS=1 唯一轮成死代码）。
- `decide()` 按 §11.8 表**首个命中**：`pass`(high_flags==0∧total≥26∧in_band)→exit 0；`revise`(≠pass∧round<MAX∧actionable_count≥1∧strictly_better∧非振荡)→exit 10；否则 `deliver-best`→exit 0 带正确 `reason` 枚举。
- `deliverable=(high_flags==0)∧in_band∧(score≥SOFT_FLOOR)`。
- **退出码 2**：`--state`/`--metrics` 不可读或 JSON 非法。**`--review`/`--critic` 不可读** → 不是 exit 2，而是 `deliver-best`+`reason=review_unavailable`+exit 0（§11.8 异常出边，见 CHECKPOINT 1 确认）。
- 状态原子改写：写 `.tmp` 再 `os.replace`。stdout 精确为 `{"decision","reason","round","total","fill_ratio","high_flags","deliverable"}`。

**验收标准**：三态可达且互斥、首个命中顺序符合 §11.8；偏序边界（带内 best 不被越界候选覆盖、EPS 并列不覆盖、red_flag 减少压过 total 微降）正确；`actionable_count==0`→`deliver-best/only_factual_gaps` 不耗轮次；`round≥MAX`→`max_rounds_reached`；缺 `--state`/坏 JSON→exit 2；`deliverable` 公式精确（score≥26 但越界→false+`layout_out_of_band`）；退出码 0/10/2 正确。

**验证命令**：
```
python3 -m unittest tests.test_polish_gate -v
# CLI 冒烟（先 cp fixture 到临时目录，避免 gate 改写只读 fixture）
tmp=$(mktemp -d); cp tests/fixtures/polish_state_init.json "$tmp/s.json"
python3 scripts/polish_gate.py --state "$tmp/s.json" --metrics tests/fixtures/metrics_inband.json \
  --review tests/fixtures/reviewer_pass.json --critic tests/fixtures/critic_clean.json --target-pages 1; echo "exit=$?"
# 期望 stdout {"decision":"pass",...,"deliverable":true} 且 exit=0
```

> **CHECKPOINT 1**：人审 (a) 三态决策表逐行对照 §11.8；(b) `review_unavailable` 退出码归属（state/metrics 不可读=exit 2；review/critic 不可读=deliver-best/exit 0）；(c) 兜底分类关键词清单忠实且不过宽。gate 决策表签字前不进入后续 wiring。

---

### Slice 2 — `page_metrics.py`（2a 整数核心 → 2b fill_ratio 增强）+ 测试 + SPEC §2 行
分两子步，让「保证正确」路径独立于不确定的估算先落地。

**改动文件**：`scripts/page_metrics.py`(新)、`tests/test_page_metrics.py`(新)、`tests/fixtures/`(抓取的 `pdfinfo`/`pdftotext -bbox` 文本片段当字符串 fixture，测解析纯函数)、`SPEC.md` §2 新行。

**2a 整数核心（保证正确，生产路径）**：复用 `ats_check.py` 的 `_has`/subprocess；`pages_int` 解析 `pdfinfo` 的 `Pages:` 行；`pdfinfo` 或 `pdftotext` 缺失 → **exit 2**（触发 §11.3 整数退化，编排按整数规则 + 评审 layout 维度兜底），不输出 fill_ratio，stderr 给 poppler 安装提示。

**2b fill_ratio 增强（可降级）**：`pdftotext -bbox <pdf> -` 出 XHTML，末页 `bottom_y=max(word.yMax)`、`text_area_height=page_height-上下边距`、`fill_ratio=floor((bottom_y-top_margin)/text_area_height, 2位)` clamp[0,1]；`pages_float=(pages_int-1)+fill_ratio`。**边距是校准未知量**：从 zh-classic `resume.cls`/geometry 读或经验标定，封装成单个文档化函数便于一行重标定。末页无词/除零退化 → 不输出假 fill_ratio，回到 exit 2 语义，stderr 记录。

**验收标准**：2a 工具在场 `pages_int` 等于 `pdfinfo`；`PATH=/usr/bin:/bin` 缺工具→exit 2、无 fill_ratio、有安装提示（仿 `test_render_scripts.py` 缺引擎用例）。2b 已知 zh-classic 单页 PDF 上 `0≤fill_ratio≤1`、两位 floor、`pages_int==1` 时 `pages_float==fill_ratio`；满页落 `[0.90,1.00]`、半空页明显<0.90。输出形状精确匹配 Slice 1 消费的 metrics JSON。

**验证命令**：
```
python3 -m unittest tests.test_page_metrics -v
PATH=/usr/bin:/bin python3 scripts/page_metrics.py any.pdf; echo "exit=$?"   # 期望 exit=2
# 工具在场（仅装了 poppler 处）：python3 scripts/page_metrics.py <zh-classic.pdf> → {"pages_int":1,"fill_ratio":0.9x,...}
```

> **CHECKPOINT 2（关键门）— fill_ratio 校准签字**：在装了 tectonic+poppler 的会话里，建真实 zh-classic PDF（满页 + 故意欠填页），跑 `page_metrics.py`，验证 `[0.90,1.00]` 能正确区分两者。**校准失败的兜底**：① 立刻按整数核心(2a)上生产，§11.3 整数退化路径已保证循环正确（band 由 layout 评审维度兜底）；② fill_ratio 维持在同一 exit-2 降级开关后，置信不足时让脚本干脆不输出 fill_ratio（恒降级），`polish_gate.py` 无需改动；③ 待校准 PDF 就绪后单函数微调边距。校准未过前，Slice 4 只接整数路径，不把 fill_ratio 接入实时循环。

---

### Slice 3 — review-agent.md / review-rubric.md schema 改写 + 契约测试
小但是真实 REVIEW spawn 的硬前置。

**改动文件**：`references/review-agent.md`（reviewer schema 34–39 每条 improvement 加 `category`/`axis`；critic schema 52–56 每条 red_flag 加 `category`/`axis`/`severity`/`needs_new_fact`；「主流程如何使用结论」60–70 改为指向 SPEC §11——交付哪版由 gate 定而非散文循环）、`references/review-rubric.md`（评分与处置 16–20 重新诠释：「≤2 必须修订」「≥26 可交付」不再=禁止交付，而是喂 §11.7/§11.8 三态裁决；加「冲突时以 §11 为准」+ `SOFT_FLOOR=24` 档）、`tests/test_review_agent_schema.py`(新，断言文档 JSON 例含 category/axis + 含 §11 交叉引用，仿 `test_skill_md.py` 子串契约风格)。

**验收标准**：reviewer 例含 `"category"`/`"axis"`；critic 例含 `"category"`/`"axis"`/`"severity"`；含「polish_gate 数字段、生成 agent 不再自行归类」(§11.6) 与可枚举标签清单；rubric 含重新诠释与「以 §11 为准」。

**验证命令**：`python3 -m unittest tests.test_review_agent_schema -v`

> **CHECKPOINT 3**：确认 reviewer/critic 文档字段与 `polish_gate.py` 实读字段（`category`/`axis`/`severity`/`needs_new_fact`/`improvements`/`red_flags` 数组名）逐一对齐——漂移会静默打断 `actionable_count`。回头核对 Slice 1 fixtures 与定稿 schema 一致。

---

### Slice 4 — 编排闭环 SKILL.md §5.5/§6 → §11 + SPEC §2 表 + e2e wiring test
集成切片，最后做（引用最终 CLI 签名/退出码/schema）。

**改动文件**：`SKILL.md` §5.5(81–84，删「直到接近整页且铺满」开环，换 §11 CALIBRATE：调 page_metrics、按落盘 fill_ratio 或整数规则判 band、单向 cal 有界调整、禁目测)、§6(94–96，换 §11 循环：ats_check→pdftotext→spawn reviewer+critic 出 category/axis JSON→polish_gate→按退出码分支 10=REVISE一轮 / 0=DELIVER 按 decision+deliverable；说明编排层初始化 polish-state.json、gate 改写之)；`SPEC.md` §2 命令表加 page_metrics.py/polish_gate.py 两行；`tests/test_e2e_polish_loop.py`(新，skip-guard 集成：纯 gate 腿用 fixture metrics 无条件跑、工具腿 skipUnless 引擎/poppler)；`tests/test_skill_md.py`(扩断言：SKILL.md 引用两个新脚本、整页/真实/子agent 旧契约仍过)。

**e2e wiring（答 F）**：
```
BUILD: fill_template → check_fidelity(fidelity_fix 有界) → build_resume.sh(build_retry 有界)
  │ 编排原子写/更新 polish-state.json
CALIBRATE: page_metrics.py
  │ exit 0 → 写 last_pages/last_fill_ratio；exit 2 → 整数退化(§11.3)，band 由 layout 评审兜底
  │ 越界 & cal<CAL_MAX & 非振荡 → 单向调整 → 回 BUILD(cal+=1)
REVIEW: ats_check→pdftotext→spawn reviewer+critic(category/axis)，每轮恰一次 → 写 last_score/last_high_flags/has_actionable
GATE: polish_gate.py --state --metrics --review --critic --target-pages N   (N=min(max_pages, ceil(自然页数)))
  │ 改写 state、打印 decision
  ├ exit 10 → round+=1,cal=0 → 回 BUILD
  ├ exit 0 decision=pass → 交付 resume.pdf (deliverable=true)
  ├ exit 0 decision=deliver-best → 交付 best；deliverable=false → resume.DRAFT.pdf + NOT-READY 横幅
  └ exit 2 → 编排当 review_unavailable → deliver-best（不重试）
```

**验收标准**：SKILL.md 不再含「直到接近整页且铺满」开环、§5.5/§6 引用 §11 有界状态机与两脚本；引用 page_metrics.py/polish_gate.py 且旧 `test_skill_md.py` 契约仍过；e2e 无工具(CI)时纯 gate 腿以合法 decision+合法改写后 state 终止、工具腿干净跳过；SPEC §2 两行退出码正确(metrics 0/2；gate 0/10/2)。

**验证命令**：
```
python3 -m unittest tests.test_e2e_polish_loop tests.test_skill_md -v
python3 -m unittest discover -s tests        # 全套，无 poppler/tectonic 须全绿
```

> **CHECKPOINT 4（终审）**：在干净(无 poppler/tectonic)机跑全套确认优雅降级；对照 §11.6 状态机审 SKILL.md 编排散文有无重新引入开环或目测；确认 §11 supersede 注记（SKILL.md §5.5/§6、review-agent.md 60–70、review-rubric.md 16–20）在所有改动文档中体现。

---

## 风险与开放项

1. **fill_ratio 校准（高，Slice 2b/CP2）**：边距是 zh-classic 专属、poppler 不给。缓解：整数核心先上且保证正确；fill_ratio 是隔离、可降级的增强，§11.3 整数退化已让特性即使推迟 fill_ratio 也完整可用。
2. **无内置 fixture PDF + CI 无引擎（中）**：`tests/fixtures/` 空、`.gitignore` 排除 PDF。采用「抓取真实 `pdfinfo`/`pdftotext -bbox` 文本存为字符串 fixture，纯函数测解析器」，CI 无工具可跑，且直测最 risky 的解析逻辑。
3. **`review_unavailable` 退出码归属（中，CP1）**：§11.8 既说 gate exit 2=输入缺失，又说评审 spawn 失败→deliver-best(exit 0)。提案：state/metrics 不可读=exit 2；review/critic 不可读=deliver-best/exit 0。CP1 确认。
4. **polish-state.json 归属（低）**：编排初始化、gate 改写；gate 须容忍缺失(按 §11.4 默认初始化)、原子 temp+rename 防损坏；测试对临时副本跑、绝不动 repo fixture。
5. **文档/测试子串契约脆性（低）**：`test_skill_md.py` 断言脚本名子串；Slice 4 须把两脚本加入其清单，否则 supersede 通过却丢引用。

---

## 端到端验证（落地后）
```
python3 -m unittest discover -s tests -v        # 全绿（CI 等价，无 poppler/tectonic）
# 装了 poppler+tectonic 的机器额外手验 CALIBRATE 真实腿（CP2 校准）：
#   建 zh-classic 满页/欠填页 → page_metrics.py → 确认 band 区分正确
# 端到端 dry-run：跑一遍 §11 wiring（init state → BUILD → CALIBRATE → REVIEW(fixture) → GATE），
#   断言：素材不足场景必终止于 deliver-best、产 resume.DRAFT.pdf + NOT-READY 横幅、polish-state.json 留审计
```

---

## 落地顺序
执行顺序：**Slice 1 → CP1 → Slice 2(2a→2b) → CP2 → Slice 3 → CP3 → Slice 4 → CP4**。任务清单见 `tasks/todo.md`。
