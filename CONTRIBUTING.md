# 贡献指南

感谢你对 CV-Forge 的兴趣！

## 开发环境

```bash
pip install -r requirements.txt
```

- Python 3.9+，脚本以 **Python 为主 + 少量 shell**，**stdlib 优先**，仅允许 `PyYAML` 一个第三方依赖。
- 测试用标准库 `unittest`，无需额外安装：`python3 -m unittest discover -s tests`。

## 运行测试

```bash
python3 -m unittest discover -s tests -v
```

## 添加一个新模板

1. 在 `assets/templates/<your-template-id>/` 下放置模板文件。
2. LaTeX 模板用占位符约定（见 `references/template-guide.md`）：`{{scalar}}`、`{{#section}}…{{/section}}`、`{{#if x}}…{{/if}}`。
3. 字体请内置在模板目录内、走相对路径，保证跨机可移植。
4. 加一份 `template.json` 元信息：`{ "id", "engine", "lang", "ats_safe", "sections" }`。
5. **务必确认模板许可证与本项目（MIT）兼容**，并在模板目录注明来源。

## 代码风格

- 脚本提供 `--help`，遵循 §2（SPEC）的命令接口与退出码约定。
- 不引入对特定机器环境的硬编码：外部依赖运行时探测，缺失给安装指引。
- 守住核心边界：**绝不生成编造内容的代码路径**（见 `references/tailoring-rules.md`）。

## 提交

- 每个改动配一个可运行的测试。
- 提交信息用祈使句，说明“做了什么 + 为什么”。
- 不要提交任何含真实 PII 的文件（`data/master-profile.*` 已被 gitignore）。
