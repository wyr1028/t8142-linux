#!/usr/bin/env python3
"""ADT 工具:生成 DTS 骨架 / 列 compatible / 找节点。

用法:
    adt2dts.py <adt>                             # 全树骨架 -> stdout
    adt2dts.py <adt> --prefix /arm-io/pmgr
    adt2dts.py <adt> --out dts/t8142-pmgr.dtsi
    adt2dts.py <adt> --compatibles-only --prefix /arm-io
    adt2dts.py <adt> --find pmgr                 # 打印匹配节点的完整路径

前缀按**去掉单元地址后的节点名**匹配,且按后缀对齐,所以
`--prefix /arm-io/pmgr` 与 `--prefix /Root/device-tree/arm-io/pmgr` 等价。

产出的骨架**不能直接编译** —— 缺 interrupt-parent / clocks / power-domains /
iommus 等引用与 (#address-cells / #size-cells) 声明,必须人工补。
节点名里的单元地址直接照搬 ADT,个别名字会被净化并标注 `/* was: ... */`。
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


def iter_paths(root):
    """产出 (node, 去掉单元地址的完整路径)。"""
    def walk(node, path):
        cur = path + "/" + base_path(node)
        yield node, cur
        for c in node.children:
            yield from walk(c, cur)

    yield from walk(root, "")


def _inside(cur: str, q: str) -> bool:
    """cur 是否在 q 这棵子树里(含 q 自身)。"""
    return cur.endswith(q) or (q + "/") in cur


def select(root, prefix: str | None, ancestors: bool = True) -> set | None:
    """返回要保留的节点 id 集合;prefix 为 None 时返回 None(表示全选)。

    ancestors=True  连前缀的祖先链一起保留(DTS 模式需要,否则嵌套会断)
    ancestors=False 只保留子树内部的节点(清单模式需要,祖先只是噪音)
    """
    if not prefix:
        return None
    q = prefix.rstrip("/")
    inside: set = set()
    with_ancestors: set = set()

    def visit(node, path: str) -> bool:
        cur = path + "/" + base_path(node)
        hit = _inside(cur, q)
        # 不能用 any(): 会在第一个 True 处短路,后面的兄弟整棵被跳过
        sub = False
        for c in node.children:
            if visit(c, cur):
                sub = True
        if hit:
            inside.add(id(node))
        if hit or sub:
            with_ancestors.add(id(node))
            return True
        return False

    visit(root, "")
    return with_ancestors if ancestors else inside


def emit(node, depth: int, out: list, keep: set | None, prefix: str | None) -> None:
    if prefix is not None and keep is not None and id(node) not in keep:
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


# ------------------------------------------------------------------ 各模式

def mode_find(root, name: str, prefix: str | None) -> str:
    keep = select(root, prefix)  # 找节点时保留祖先语义无所谓,只筛范围
    rows = []
    for node, path in iter_paths(root):
        if prefix is not None and keep is not None and id(node) not in keep:
            continue
        if node.base_name == name:
            rows.append(path)
    if not rows:
        return "没有名为 %s 的节点\n" % name
    return "\n".join(rows) + "\n"


def mode_compatibles(root, prefix: str | None) -> str:
    keep = select(root, prefix, ancestors=False)
    rows = set()
    for node, _ in iter_paths(root):
        if prefix is not None and keep is not None and id(node) not in keep:
            continue
        if node.compatible:
            rows.add("%s\t%s" % (node.compatible[0], node.name))
    return "\n".join(sorted(rows)) + "\n"


def mode_dts(root, prefix: str | None, src_name: str) -> str:
    keep = select(root, prefix)
    out = [
        "/* 由 tools/adt2dts.py 从 %s 生成的骨架" % src_name,
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
    emit(root, 0, out, keep, prefix)
    out += ["};", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("adt", help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("--prefix", help="只处理该子树,如 /arm-io/pmgr")
    ap.add_argument("--out", help="输出文件(默认 stdout)")
    ap.add_argument("--compatibles-only", action="store_true", help="只列 compatible")
    ap.add_argument("--find", metavar="NAME", help="打印匹配节点的完整路径")
    args = ap.parse_args()

    root = adtlib.load(args.adt)
    src = Path(args.adt).name

    if args.find:
        text = mode_find(root, args.find, args.prefix)
    elif args.compatibles_only:
        text = mode_compatibles(root, args.prefix)
    else:
        text = mode_dts(root, args.prefix, src)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("已写入 %s(%d 行)" % (args.out, text.count("\n")), file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
