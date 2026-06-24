"""依赖自愈：用户无需手动配置 Python 环境。

脚本调用 load_yaml/dump_yaml 即可；若缺 PyYAML，会自动静默安装后重试，
失败再给清晰提示。这样使用者不必预先 `pip install`。
"""
import subprocess
import sys


def _import_yaml():
    try:
        import yaml  # noqa: F401
        return yaml
    except ImportError:
        # 自动安装一次，用户无感
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "pyyaml"],
                check=True,
            )
            import yaml  # noqa: F811
            return yaml
        except Exception:
            sys.stderr.write(
                "需要 PyYAML 但自动安装失败。请手动执行：\n"
                "    %s -m pip install pyyaml\n" % sys.executable
            )
            raise


def load_yaml(path):
    yaml = _import_yaml()
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data):
    yaml = _import_yaml()
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
