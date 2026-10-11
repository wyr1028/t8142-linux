#!/usr/bin/env python3
"""从 ADT 生成 DTS 骨架。

产出的是**骨架,不是可编译的 DTS** —— 缺 interrupt-parent / clocks /
power-domains / iommus 这些引用,必须人工补。目的是把成百个节点一次性
摆成正确形状并带上 compatible,而不是手抄。

用法:
    python3 tools/adt2dts.py ~/m5-adt.plist                        # 全树
    python3 tools/adt2dts.py ~/m5-adt.plist --prefix /arm-io/pmgr
    python3 tools/adt2dts.py raw-adt.dtb --out dts/t8142-pmgr.dtsi
    python3 tools/adt2dts.py raw-adt.dtb --compatibles-only

前缀按**去掉单元地址后的节点名**匹配,匹配到的地方按后缀对齐,
所以 `--prefix /arm-io/pmgr` 和 `--prefix /device-tree/arm-io/pmgr` 等价。

节点名里的单元地址直接照搬 ADT,可能不是 DTS 要求的十六进制形式;
个别名字会被净化,输出里带 `/* was: ... */` 标注。
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adtlib  # noqa: E402

_INVALID = re.compile(r"[^A-Za-z0-9,._+@-]")


def dts_name(name: str) -> tuple:
    """返回 (净化后的名字, 原名或 None)。"""
    if not name or name == "/":
        return "/", None
    clean = _INVALID.sub("_", name)
    if clean.startswith("@"):
        clean = "_" + clean
    return (clean, None) if clean == name else (clean, name)


def dts_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def base_path(node) -> str:
    return dts_name(node.base_name)[0]


def select(root, prefix: str | None) -> set:
    """返回要输出的节点 id 集合;prefix 为 None 表示全选。"""
    if not prefix:
        return set()
    q = prefix.rstrip("/")
    keep: set = set()

    def visit(node, path: str) -> bool:
        cur = path + "/" + base_path(node)
        # 命中:后缀对齐到 prefix 本身,或 prefix 作为整段出现在路径中间
        # (后者覆盖"prefix 之下的更深节点",如 /arm-io 下的 /arm-io/pmgr)
        hit = cur.endswith(q) or (q + "/") in cur
        # 注意不能用 any(): 它会在第一个 True 处短路,导致后面的兄弟节点整棵被跳过
        below = False
        for c in node.children:
            if visit(c, cur):
                below = True
        if hit or below:
            keep.add(id(node))
            return True
        return False

    visit(root, "")
    return keep


def emit(node, depth: int, out: list, keep: set, prefix: str | None) -> None:
    if prefix is not None and id(node) not in keep:
        return

    name, orig = dts_name(node.name)
    ind = "\t" * depth

    if depth > 0:
        suffix = "  /* was: %s */" % orig if orig else ""
        out.append("%s%s {%s" % (ind, name, suffix))

    if node.compatible:
        out.append("%s\tcompatible = %s;" % (ind, ", ".join(dts_str(x) for x in node.compatible)))

    dt = node.device_type
    if dt:
        out.append("%s\tdevice_type = %s;" % (ind, dts_str(dt)))

    cells = node.reg_cells
    if cells:
        out.append("%s\treg = <%s>;  /* 原始 cell,未按 #address-cells 解释 */"
                   % (ind, " ".join(cells)))
    elif "reg" in node.props:
        out.append("%s\t/* reg 长度非 4 字节对齐,已跳过 */" % ind)

    for child in node.children:
        emit(child, depth + 1, out, keep, prefix)

    if depth > 0:
        out.append("%s};" % ind)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("adt", help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("--prefix", help="只输出该子树,如 /arm-io/pmgr")
    ap.add_argument("--out", help="输出文件(默认 stdout)")
    ap.add_argument("--compatibles-only", action="store_true", help="只列 compatible")
    args = ap.parse_args()

    root = adtlib.load(args.adt)

    if args.compatibles_only:
        keep = select(root, args.prefix)
        rows = []
        for n, _ in root.walk():
            if args.prefix and id(n) not in keep:
                continue
            if n.compatible:
                rows.append("%s\t%s" % (n.compatible[0], n.name))
        text = "\n".join(sorted(set(rows))) + "\n"
    else:
        keep = select(root, args.prefix)
        out = [
            "/* 由 tools/adt2dts.py 从 %s 生成的骨架" % Path(args.adt).name,
            " * 生成日期: %s" % date.today().isoformat(),
            " * ⚠️ 不能直接编译 —— 缺 interrupt-parent / clocks / power-domains / iommus",
            " *    等引用,以及 (#address-cells / #size-cells) 声明,需人工补。",
            " * 来源纪律见 docs/PROVENANCE.md。",
            " */",
            "",
            "/dts-v1/;",
            "",
            "/ {",
        ]
        emit(root, 0, out, keep, args.prefix)
        out += ["};", ""]
        text = "\n".join(out)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("已写入 %s(%d 行)" % (args.out, text.count("\n")), file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
