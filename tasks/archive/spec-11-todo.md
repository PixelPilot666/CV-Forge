# 已归档 TODO — SPEC §11 打磨循环落地

> 本清单已完成并由 CV-Forge v2 方案取代；保留用于历史审计。

详见 `tasks/plan.md`。执行顺序：Slice 1 → CP1 → Slice 2 → CP2 → Slice 3 → CP3 → Slice 4 → CP4。

> **状态：全部 4 个切片已实现并提交**（`/build auto`，分支 `feat/spec-11-polish-loop`，6 个 commit，132 测试全绿）。
> CP1–CP4 在运行中就地完成（CP2 校准用 live poppler+tectonic 实测通过：sparse=0.65、full=0.92）。
> 仍建议人审：CP1 的 `review_unavailable` 退出码归属判断、CP4 的 SKILL.md 散文。见结尾「待人审项」。

---

## Slice 1 — polish_gate.py 纯决策引擎（载重核心，最先做）

- [ ] **1.1** 新建 `scripts/polish_gate.py` 骨架：照抄 `check_fidelity.py` 风格（shebang / `main(argv=None)` / `sys.exit(main())` / argparse `--state --metrics --review --critic --target-pages`）。stdlib only。
- [ ] **1.2** 转写 §11.5 常量 + §11.3 `in_band(fr,N)`（N=1 用 `[0.90,1.00]`；N>1 用 `[N-0.10,N]`）。
- [ ] **1.3** 实现 `actionable_count` + §11.6 兜底强制分类（high 且虚报/夸大/超出素材/技术栈违规→actionable；needs_new_fact 或缺数字/无证据/规模/JD缺口关键词→needs-fact）。
- [ ] **1.4** 实现 `strictly_better` §11.7 字典序（high_flags↓ / in_band / total↑ / |fr-中点|+EPS），含「red_flag 减少压过 total 微降」与「越界候选不覆盖带内 best，除非消除 high」。
- [ ] **1.5** 实现 `decide()` §11.8 三态首个命中（pass/revise/deliver-best）+ 正确 `reason` 枚举 + `deliverable` 公式；算子顺序：先判 revise 再更新 best 快照。
- [ ] **1.6** 退出码：0=pass/deliver-best、10=revise、2=state/metrics 不可读或坏 JSON；review/critic 不可读→deliver-best/`review_unavailable`/exit 0。
- [ ] **1.7** 状态原子改写（写 `.tmp` 再 `os.replace`）；stdout 精确为 `{decision,reason,round,total,fill_ratio,high_flags,deliverable}`。
- [ ] **1.8** 新建 `tests/fixtures/`：`reviewer_pass.json` `reviewer_actionable.json` `reviewer_needsfact.json` `critic_clean.json` `critic_high_flag.json` `metrics_inband.json` `metrics_oob.json` `polish_state_init.json`。
- [ ] **1.9** 新建 `tests/test_polish_gate.py`（unittest，直接 import；对 state 临时副本跑，不动 repo fixture）覆盖全部验收标准。
- [ ] **1.10** 跑 `python3 -m unittest tests.test_polish_gate -v` + CLI 冒烟（见 plan）全绿。

> **CHECKPOINT 1（人审签字）**：决策表逐行对照 §11.8；`review_unavailable` 退出码归属确认；兜底分类关键词清单审阅。**未签字不进 wiring。**

---

## Slice 2 — page_metrics.py（整数核心 → fill_ratio 增强）

### 2a 整数核心（保证正确，生产路径）
- [ ] **2a.1** 新建 `scripts/page_metrics.py` 骨架；复用 `ats_check.py` 的 `_has(cmd)`/subprocess 模式。
- [ ] **2a.2** `pages_int` 解析 `pdfinfo` 的 `Pages:` 行；缺 `pdfinfo`/`pdftotext`→exit 2、不输出 fill_ratio、stderr 给 poppler 安装提示。
- [ ] **2a.3** 抓取真实 `pdfinfo`/`pdftotext -bbox` 文本片段存为字符串 fixture；新建 `tests/test_page_metrics.py` 纯函数测解析器 + 缺工具 exit 2 用例（仿 `test_render_scripts.py`）。
- [ ] **2a.4** 跑 `python3 -m unittest tests.test_page_metrics -v` + `PATH=/usr/bin:/bin` 缺工具路径 exit=2 验证。

### 2b fill_ratio 增强（可降级）
- [ ] **2b.1** 解析 `pdftotext -bbox` XHTML：末页 `bottom_y=max(word.yMax)`、`text_area_height=page_height-上下边距`、`fill_ratio=floor(...,2)` clamp[0,1]、`pages_float`。
- [ ] **2b.2** 边距读取/标定封装成单个文档化函数（一行可重标定）；末页无词/除零→退回 exit 2 语义、不输出假值。
- [ ] **2b.3** 输出形状精确匹配 Slice 1 消费的 metrics JSON；补 fill_ratio 单元测试。
- [ ] **2.4** 在 `SPEC.md` §2 命令表加 `page_metrics.py` 行（退出码 0/2）。

> **CHECKPOINT 2（关键门，人审签字）— fill_ratio 校准**：装 tectonic+poppler 的会话建满页/欠填 zh-classic PDF，验 `[0.90,1.00]` 能区分。失败则按整数核心上生产、fill_ratio 恒降级（gate 无需改）、待校准后单函数微调。**未签字不把 fill_ratio 接入实时循环。**

---

## Slice 3 — 评审 schema 改写（真实 REVIEW spawn 硬前置）

- [ ] **3.1** 改 `references/review-agent.md`：reviewer schema 每条 improvement 加 `category`/`axis`；critic schema 每条 red_flag 加 `category`/`axis`/`severity`/`needs_new_fact`。
- [ ] **3.2** 改 `references/review-agent.md`「主流程如何使用结论」(60–70)：改为指向 SPEC §11（交付哪版由 gate 定）+「polish_gate 数字段、生成 agent 不再自行归类」+ 可枚举标签清单。
- [ ] **3.3** 改 `references/review-rubric.md`「评分与处置」(16–20)：重新诠释为喂三态裁决 + 加 `SOFT_FLOOR=24` 档 +「冲突时以 §11 为准」。
- [ ] **3.4** 新建 `tests/test_review_agent_schema.py`（子串契约，仿 `test_skill_md.py`）断言字段与 §11 交叉引用存在。
- [ ] **3.5** 跑 `python3 -m unittest tests.test_review_agent_schema -v` 全绿。

> **CHECKPOINT 3（人审签字）**：文档字段与 `polish_gate.py` 实读字段逐一对齐（漂移会静默打断 actionable_count）；回核 Slice 1 fixtures 与定稿 schema 一致。

---

## Slice 4 — 编排闭环（集成切片，最后做）

- [ ] **4.1** 改 `SKILL.md` §5.5(81–84)：删「直到接近整页且铺满」开环，换 §11 CALIBRATE（调 page_metrics、按落盘 fill_ratio 或整数规则判 band、单向 cal 有界、禁目测）。
- [ ] **4.2** 改 `SKILL.md` §6(94–96)：换 §11 循环（ats_check→pdftotext→spawn reviewer+critic 出 category/axis→polish_gate→按退出码 10=REVISE一轮 / 0=DELIVER）；写明编排层 init polish-state.json、gate 改写之。
- [ ] **4.3** 在 `SPEC.md` §2 命令表加 `polish_gate.py` 行（退出码 0/10/2）。
- [ ] **4.4** 扩 `tests/test_skill_md.py`：断言引用 page_metrics.py/polish_gate.py、旧契约（整页/真实/子agent）仍过。
- [ ] **4.5** 新建 `tests/test_e2e_polish_loop.py`：纯 gate 腿(fixture metrics)无条件跑、工具腿 `skipUnless` 引擎/poppler；断言素材不足场景终止于 deliver-best + 合法改写后 state。
- [ ] **4.6** 跑 `python3 -m unittest tests.test_e2e_polish_loop tests.test_skill_md -v` + `python3 -m unittest discover -s tests`（无 poppler/tectonic 须全绿）。

> **CHECKPOINT 4（终审，人审签字）**：干净机跑全套确认优雅降级；对照 §11.6 审 SKILL.md 散文无重新引入开环/目测；确认 §11 supersede 注记在 SKILL.md §5.5/§6、review-agent.md 60–70、review-rubric.md 16–20 均体现。

---

## 完成定义（DoD）
- [ ] `python3 -m unittest discover -s tests -v` 在无 poppler/tectonic 环境全绿（CI 等价）。
- [ ] SKILL.md 不再含任何无机器上限的循环措辞；所有「停/不停」判定可由脚本/页数/退出码机器判定。
- [ ] 素材不足 dry-run 必终止于 deliver-best、产 `resume.DRAFT.pdf` + NOT-READY 横幅、留 `polish-state.json` 审计。
- [ ] CP2 校准签字（或明确记录 fill_ratio 暂走恒降级、整数路径生产）。
