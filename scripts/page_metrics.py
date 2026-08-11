#!/usr/bin/env python3
"""页数 + 末页填充比（SPEC §11.3 的确定性度量）。

容差带判定（§11.7）的全部依据是 fill_ratio = 末页正文最底边 / 版心高度。`pdfinfo`
只给整数 Pages，不给小数，所以这里用 `pdftotext -bbox` 取末页最底部文本框的 yMax 估算。
这是把"接近整页且铺满"这类肉眼判断换成机器可判定值的唯一来源——agent 不得目测。

整数优先、估算可降级（§11.3）：缺 pdfinfo/pdftotext，或末页取不到文本框时，
**不输出假 fill_ratio**，退出码 2，触发编排层的整数退化路径（页数 + 评审 layout 维度兜底）。

用法:
    python3 scripts/page_metrics.py <resume.pdf>
输出(stdout, JSON): {"pages_int":1,"fill_ratio":0.94,"pages_float":0.94}
退出码: 0 = 成功(含 fill_ratio); 2 = 工具缺失/末页无文本框(走整数退化, 不输出 fill_ratio)。
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from shutil import which

# ── zh-classic 模板版心标定（resume.cls geometry: a4paper, top=0.50in, bottom=0.5in）──
# A4 高 841.89pt；上下边距各 0.5in = 36pt。改模板时只需调这三个常量重标定。
PAGE_HEIGHT_PT = 841.89
TOP_MARGIN_PT = 36.0      # 0.50in
BOTTOM_MARGIN_PT = 36.0   # 0.50in


def parse_pages(pdfinfo_text):
    """从 `pdfinfo` 输出解析整数页数；找不到 Pages 行返回 None。"""
    m = re.search(r"^Pages:\s*(\d+)", pdfinfo_text, re.MULTILINE)
    return int(m.group(1)) if m else None


def _floor2(x):
    """向下取两位小数（与 §11.3"按两位小数 floor"一致）。"""
    return math.floor(x * 100) / 100.0


def fill_ratio_from_bbox(bbox_xml,
                         page_height=PAGE_HEIGHT_PT,
                         top=TOP_MARGIN_PT, bottom=BOTTOM_MARGIN_PT):
    """从 `pdftotext -bbox` 的 XHTML 估算**末页**填充比，两位 floor、clamp 到 [0,1]。

    末页 bottom_y = max(word.yMax)；版心高度 = page_height - top - bottom；
    fill_ratio = (bottom_y - top) / 版心高度。末页无文本框返回 None（→ 整数退化）。
    """
    pages = bbox_xml.split("<page")
    if len(pages) < 2:
        return None
    last = pages[-1]
    ymaxes = [float(m) for m in re.findall(r'yMax="([\d.]+)"', last)]
    if not ymaxes:
        return None
    # 末页可能声明了自己的高度，优先用它（多页/异形页更准）
    hm = re.search(r'height="([\d.]+)"', last)
    ph = float(hm.group(1)) if hm else page_height
    text_area = ph - top - bottom
    if text_area <= 0:
        return None
    fr = (max(ymaxes) - top) / text_area
    fr = max(0.0, min(1.0, fr))
    return _floor2(fr)


def _has(cmd):
    return which(cmd) is not None


def _hint():
    sys.stderr.write(
        "提示: 未找到 pdfinfo/pdftotext，无法机器度量页数与填充比，按整数退化路径处理。\n"
        "  macOS: brew install poppler；Ubuntu: apt install poppler-utils\n"
    )


def analyze(pdf_path):
    """返回 (pages_int, fill_ratio)；任一不可得时对应位置为 None。"""
    if not (_has("pdfinfo") and _has("pdftotext")):
        return None, None
    info = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
    pages = parse_pages(info.stdout) if info.returncode == 0 else None
    bbox = subprocess.run(["pdftotext", "-bbox", pdf_path, "-"],
                          capture_output=True, text=True)
    fr = fill_ratio_from_bbox(bbox.stdout) if bbox.returncode == 0 else None
    return pages, fr


def main(argv=None):
    parser = argparse.ArgumentParser(description="页数 + 末页填充比度量")
    parser.add_argument("pdf", help="渲染后的 resume.pdf")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.pdf):
        print(f"错误: 找不到 PDF: {args.pdf}", file=sys.stderr)
        return 2

    pages, fr = analyze(args.pdf)
    if pages is None or fr is None:
        # 整数退化：不输出假 fill_ratio（§11.3 硬规则 1/2）
        _hint()
        if pages is not None:
            print(json.dumps({"pages_int": pages}, ensure_ascii=False))
        return 2

    pages_float = (pages - 1) + fr
    print(json.dumps({"pages_int": pages, "fill_ratio": fr,
                      "pages_float": round(pages_float, 2)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
