#!/usr/bin/env bash
# 探测可用的 XeLaTeX 引擎，输出 JSON。
# 退出码: 0 = 至少有一个可用; 1 = 都没有。
#
# 输出示例:
#   {"available":true,"engine":"tectonic","candidates":{"tectonic":true,"xelatex":false,"latexmk":false}}
#
# 兼容 bash 3.2(macOS 自带)，不使用关联数组等 bash4+ 特性。
set -u

# 候选引擎，按优先级排列(tectonic 首选: 单二进制、按需下载宏包)
CANDIDATES="tectonic xelatex latexmk"

chosen=""
cand_json=""
for e in $CANDIDATES; do
  if command -v "$e" >/dev/null 2>&1; then
    avail=true
    if [ -z "$chosen" ]; then chosen="$e"; fi
  else
    avail=false
  fi
  [ -n "$cand_json" ] && cand_json="$cand_json,"
  cand_json="$cand_json\"$e\":$avail"
done

if [ -n "$chosen" ]; then
  printf '{"available":true,"engine":"%s","candidates":{%s}}\n' "$chosen" "$cand_json"
  exit 0
else
  printf '{"available":false,"engine":null,"candidates":{%s}}\n' "$cand_json"
  exit 1
fi
