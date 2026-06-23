#!/usr/bin/env bash
# 用探测到的引擎把 resume.tex 编译为 PDF。
# 用法: render_pdf.sh <resume.tex> [-o <outdir>]
# 退出码: 0 = 成功; 2 = 输入缺失; 3 = 无可用引擎(含安装指引); 1 = 编译失败。
#
# 注: 模板字体走相对路径，编译需在含模板资源(resume.cls/*.sty/fonts/)的目录中进行。
#     调用方应先把模板资源与 resume.tex 放在同一 outdir。
set -u

TEX=""
OUTDIR="."
while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output) OUTDIR="$2"; shift 2 ;;
    *) TEX="$1"; shift ;;
  esac
done

if [ -z "$TEX" ] || [ ! -f "$TEX" ]; then
  echo "错误: 找不到输入文件: ${TEX:-<空>}" >&2
  exit 2
fi

# 探测引擎
detect_os_hint() {
  case "$(uname -s)" in
    Darwin) echo "  macOS:        brew install tectonic" ;;
    Linux)  echo "  Debian/Ubuntu: apt install texlive-xetex   # 或下载 tectonic release" ;;
    *)      echo "  Windows:      winget install tectonic       # 或 scoop install tectonic" ;;
  esac
}

ENGINE=""
for e in tectonic xelatex latexmk; do
  if command -v "$e" >/dev/null 2>&1; then ENGINE="$e"; break; fi
done

if [ -z "$ENGINE" ]; then
  {
    echo "❌ 未找到 LaTeX 引擎(tectonic / xelatex / latexmk)。"
    echo "请先安装一个 XeLaTeX 引擎(推荐 tectonic，单二进制、跨平台):"
    detect_os_hint
    echo "安装后重试即可；本工具不会在缺引擎时静默降级。"
  } >&2
  exit 3
fi

mkdir -p "$OUTDIR"
TEXNAME="$(basename "$TEX")"
# 若 tex 不在 outdir，复制过去(字体等资源应已由调用方就位)
if [ "$(cd "$(dirname "$TEX")" && pwd)" != "$(cd "$OUTDIR" && pwd)" ]; then
  cp "$TEX" "$OUTDIR/$TEXNAME"
fi

echo "▶ 使用引擎 $ENGINE 编译 $TEXNAME ..." >&2
case "$ENGINE" in
  tectonic)
    ( cd "$OUTDIR" && tectonic "$TEXNAME" ) ;;
  xelatex)
    # 跑两遍以稳定引用/目录
    ( cd "$OUTDIR" && xelatex -interaction=nonstopmode "$TEXNAME" >/dev/null \
        && xelatex -interaction=nonstopmode "$TEXNAME" >/dev/null ) ;;
  latexmk)
    ( cd "$OUTDIR" && latexmk -xelatex -interaction=nonstopmode "$TEXNAME" >/dev/null ) ;;
esac
status=$?

PDF="$OUTDIR/${TEXNAME%.tex}.pdf"
if [ $status -eq 0 ] && [ -f "$PDF" ]; then
  echo "✅ 已生成 $PDF" >&2
  echo "$PDF"
  exit 0
else
  echo "❌ 编译失败(引擎 $ENGINE, 退出码 $status)。" >&2
  exit 1
fi
