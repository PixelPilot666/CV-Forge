#!/usr/bin/env python3
"""Finalize a generated PDF as formal or DRAFT from polish-state.json only.

This script does not reinterpret reviewer scores. It accepts a formal delivery
only when the gate reached a terminal, deliverable state for the current review
round and the selected snapshot has no high-severity flags.
"""
import argparse
import json
import os
import shutil
import sys


TERMINAL_DECISIONS = ("pass", "deliver-best")


def _snapshot_page_ok(state, snapshot):
    target_pages = state.get("page_target", 1)
    page_ok = snapshot.get("page_ok")
    if page_ok is None:
        page_ok = snapshot.get("pages") == target_pages
    elif snapshot.get("pages") is not None:
        page_ok = bool(page_ok) and snapshot.get("pages") == target_pages
    return bool(page_ok)


def _delivery_snapshot(state):
    """Return metadata for the materialized PDF; fall back for older states."""
    return state.get("selected") or state.get("best") or {}


def is_formal_delivery(state):
    """Return whether state is safe to expose as the canonical resume.pdf."""
    selected = _delivery_snapshot(state)
    return (
        state.get("terminated") is True
        and state.get("decision") in TERMINAL_DECISIONS
        and state.get("deliverable") is True
        and selected.get("high_flags") == 0
        and _snapshot_page_ok(state, selected)
        and state.get("last_review_round") == state.get("round")
    )


def _put_pdf(source, target):
    source = os.path.abspath(source)
    target = os.path.abspath(target)
    if source == target:
        return
    if os.path.dirname(source) == os.path.dirname(target):
        os.replace(source, target)
    else:
        shutil.copy2(source, target)


def finalize(state, pdf_path, out_dir):
    """Name the PDF from gate state and return a report-ready JSON summary."""
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)

    os.makedirs(out_dir, exist_ok=True)
    formal = is_formal_delivery(state)
    filename = "resume.pdf" if formal else "resume.DRAFT.pdf"
    target = os.path.join(out_dir, filename)
    opposite = os.path.join(
        out_dir, "resume.DRAFT.pdf" if formal else "resume.pdf")

    _put_pdf(pdf_path, target)
    if os.path.isfile(opposite) and os.path.abspath(opposite) != os.path.abspath(target):
        os.remove(opposite)

    selected = _delivery_snapshot(state)
    return {
        "decision": state.get("decision"),
        "deliverable": state.get("deliverable"),
        "delivery_reason": state.get("delivery_reason"),
        "score": selected.get("score"),
        "high_flags": selected.get("high_flags"),
        "page_ok": _snapshot_page_ok(state, selected),
        "density_warning": state.get("last_density_warning"),
        "round": state.get("round"),
        "last_review_round": state.get("last_review_round"),
        "file": filename,
        "formal": formal,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="按 polish-state.json 确定正式版或 DRAFT 文件名")
    parser.add_argument("--state", required=True, help="polish-state.json")
    parser.add_argument("--pdf", required=True, help="本轮刚编译的 PDF")
    parser.add_argument("--out-dir", required=True, help="交付目录")
    args = parser.parse_args(argv)

    try:
        with open(args.state, encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ValueError("state 顶层必须是 JSON object")
        summary = finalize(state, args.pdf, args.out_dir)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as ex:
        print(f"错误: 无法完成交付: {ex}", file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
