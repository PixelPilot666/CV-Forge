#!/usr/bin/env bash
# 在临时构建目录里编译简历，只把成品 resume.pdf 放回产物目录。
#
# 为什么要这样做：resume.cls / *.sty 用相对路径引用 fonts/、images/，所以 .tex 必须
# 与这些资源同目录才能编译。早期做法是把整套模板(含 ~43MB Adobe 中文字体)复制进每一个
# 产物目录——用户每投一个岗位就多占 ~43MB，产物目录也被字体淹没。本脚本改为在临时目录里
# 就位资源、编译，再只回收 PDF，让产物目录保持精简(resume.pdf / resume.tex /
# tailor.json / match-report.md)。字体已嵌进 PDF，成品可直接投递。
#
# 用法: build_resume.sh <resume.tex> -t <模板目录> -o <产物目录> [--photo <jpg>] [--keep-source]
# 退出码: 0 成功; 2 输入缺失; 3 无可用引擎(render_pdf.sh 给安装指引); 1 编译失败。
set -u

TEX=""
TMPL=""
OUTDIR="."
PHOTO=""
KEEP_SOURCE=1   # 默认把人可编辑的 resume.tex 也放进产物目录
while [ $# -gt 0 ]; do
  case "$1" in
    -t|--template) TMPL="$2"; shift 2 ;;
    -o|--output)   OUTDIR="$2"; shift 2 ;;
    --photo)       PHOTO="$2"; shift 2 ;;
    --no-source)   KEEP_SOURCE=0; shift ;;
    *)             TEX="$1"; shift ;;
  esac
done

if [ -z "$TEX" ] || [ ! -f "$TEX" ]; then
  echo "错误: 找不到输入 .tex: ${TEX:-<空>}" >&2; exit 2
fi
if [ -z "$TMPL" ] || [ ! -d "$TMPL" ]; then
  echo "错误: 找不到模板目录(-t): ${TMPL:-<空>}" >&2; exit 2
fi

HERE="$(cd "$(dirname "$0")" && pwd)"

# 临时构建目录，退出时无条件清理
BUILD="$(mktemp -d "${TMPDIR:-/tmp}/cv-forge-build.XXXXXX")" \
  || { echo "错误: 无法创建临时构建目录" >&2; exit 1; }
cleanup() { rm -rf "$BUILD"; }
trap cleanup EXIT

# 就位模板资源(fonts/cls/sty/images) + 待编译 tex
cp -R "$TMPL/." "$BUILD/"
cp "$TEX" "$BUILD/resume.tex"

# 照片：resume.cls 引用 images/you.jpg。有用户照片就用，否则用自带占位图兜底，
# 保证 photo:true 时也能编译；photo:false 时模板不引用照片，兜底无副作用。
mkdir -p "$BUILD/images"
if [ -n "$PHOTO" ] && [ -f "$PHOTO" ]; then
  cp "$PHOTO" "$BUILD/images/you.jpg"
elif [ ! -f "$BUILD/images/you.jpg" ] && [ -f "$BUILD/images/placeholder.jpg" ]; then
  cp "$BUILD/images/placeholder.jpg" "$BUILD/images/you.jpg"
fi

# 编译：复用 render_pdf.sh 的引擎探测与容错(它在 BUILD 内 cd 编译，字体走相对路径)
bash "$HERE/render_pdf.sh" "$BUILD/resume.tex" -o "$BUILD" >/dev/null
status=$?
if [ $status -ne 0 ] || [ ! -f "$BUILD/resume.pdf" ]; then
  # render_pdf.sh 已把诊断(含缺引擎的安装指引)打到 stderr，原样透出
  exit $status
fi

mkdir -p "$OUTDIR"
cp "$BUILD/resume.pdf" "$OUTDIR/resume.pdf"
# 把人可编辑的源码也留在产物目录(便于二次修改；重新出 PDF 时再次跑本脚本即可重新铺字体)
if [ "$KEEP_SOURCE" -eq 1 ]; then
  SRC_ABS="$(cd "$(dirname "$TEX")" && pwd)/$(basename "$TEX")"
  OUT_TEX="$(cd "$OUTDIR" && pwd)/resume.tex"
  if [ "$SRC_ABS" != "$OUT_TEX" ]; then
    cp "$TEX" "$OUTDIR/resume.tex"
  fi
fi

echo "✅ 已生成 $OUTDIR/resume.pdf（产物目录精简，字体已嵌入 PDF）" >&2
echo "$OUTDIR/resume.pdf"
exit 0
