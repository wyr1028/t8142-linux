#!/usr/bin/env python3
"""ADT compatible 与源码引用字面量的差集。

用途:找出"这台机器上有、但某代码库不认识"的设备块。
docs/HARDWARE.md §4 那 25 条就是本脚本跑出来的 —— 这个脚本是它的**复现工具**。

用法:
    python3 tools/compat_diff.py ~/m5-adt.plist ~/some-repo/src
    python3 tools/compat_diff.py ~/m5-adt.plist ~/repo/src --all    # 不限版本号形式
    python3 tools/compat_diff.py ~/m5-adt.plist ~/repo/src --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adtlib  # noqa: E402

# 默认只收带 SoC 版本号的形态,如 atc-phy,t8132 / apple,t8122-aic3
RE_VERSIONED = re.compile(r'"([A-Za-z0-9_-]+,[ts]\d{3,4}[A-Za-z0-9_-]*)"')
# --all:任何 xxx,yyy 形态
RE_ANY = re.compile(r'"([A-Za-z0-9_-]+,[A-Za-z0-9_-]+)"')
# 不带引号的同款,用来筛 ADT 侧已经解出来的字符串
FULL_VERSIONED = re.compile(r"[A-Za-z0-9_-]+,[ts]\d{3,4}[A-Za-z0-9_-]*")
FULL_ANY = re.compile(r"[A-Za-z0-9_-]+,[A-Za-z0-9_-]+")

SKIP_DIRS = {".git", "target", "build", "out", "__pycache__", ".venv", "venv", "node_modules"}
SKIP_EXT = {".o", ".a", ".so", ".dylib", ".bin", ".dtb", ".elf", ".png", ".jpg", ".pdf", ".zip"}


def adt_compatibles(path: str) -> dict:
    """compatible -> 出现的节点名列表(按首次出现顺序)。"""
    root = adtlib.load(path)
    out: dict = {}
    for n, _ in root.walk():
        for c in n.compatible:
            out.setdefault(c, [])
            if n.name not in out[c]:
                out[c].append(n.name)
    return out


def source_literals(root: str, pattern: re.Pattern) -> set:
    found = set()
    for p in Path(root).rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix in SKIP_EXT:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        found.update(pattern.findall(text))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("adt", help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("srcdir", help="源码目录")
    ap.add_argument("--all", action="store_true", help="不限版本号形态")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--soc", metavar="ID",
                    help="本机 SoC 号(如 t8142):把'只有 ADT 有'拆成"
                         "'本 SoC 新增'与'复用旧代代号'两组")
    args = ap.parse_args()

    src_pattern = RE_ANY if args.all else RE_VERSIONED
    adt_pattern = FULL_ANY if args.all else FULL_VERSIONED
    adt = adt_compatibles(args.adt)
    known = source_literals(args.srcdir, src_pattern)

    # 两侧用同一把尺子,否则 ADT 侧会把 ARM,v8 这类也算进来
    adt_set = {c for c in adt if c and adt_pattern.fullmatch(c)}
    both = sorted(adt_set & known)
    only_adt = sorted(adt_set - known)
    only_src = sorted(known - adt_set)

    tag = "," + args.soc if args.soc else None
    new_blocks = [c for c in only_adt if tag and tag in c] if tag else []
    reused = [c for c in only_adt if not (tag and tag in c)] if tag else []

    if args.json:
        out = {
            "adt_total": len(adt_set),
            "source_total": len(known),
            "both": both,
            "only_in_adt": [{"compatible": c, "nodes": adt[c]} for c in only_adt],
            "only_in_source": only_src,
        }
        if tag:
            out["new_for_soc"] = [{"compatible": c, "nodes": adt[c]} for c in new_blocks]
            out["reused_older"] = [{"compatible": c, "nodes": adt[c]} for c in reused]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print("ADT compatible: %d  源码字面量: %d  交集: %d" % (len(adt_set), len(known), len(both)))

    print("\n=== 两边都有(可能直接可用)===")
    for c in both:
        print("  %-42s x%-3d e.g. %s" % (c, len(adt[c]), adt[c][0]))

    def dump(title: str, items: list) -> None:
        print("\n=== %s  %d 条 ===" % (title, len(items)))
        for c in items:
            print("  %-42s x%-3d e.g. %s" % (c, len(adt[c]), adt[c][0]))

    if tag:
        dump("只有 ADT 有,且带 %s(本 SoC 新增,需要新表项)" % tag, new_blocks)
        dump("只有 ADT 有,但用旧代代号(疑似可复用)", reused)
    else:
        dump("只有 ADT 有(源码不认识,需要新表项)", only_adt)

    print("\n=== 只有源码有(本机没有该节点)===")
    for c in only_src:
        print("  %s" % c)

    return 0


if __name__ == "__main__":
    sys.exit(main())
