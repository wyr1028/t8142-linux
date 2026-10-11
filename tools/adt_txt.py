#!/usr/bin/env python3
"""解析 **原始 ADT 的文本 dump**(m1n1 风格)。

## 为什么需要这个

`ioreg` 给的是**翻译后**的视图,而 `.dts` 要的是**翻译前**的物理地址。
真正的原始 ADT 是 Apple 自己的二进制格式(魔数 `0x17`,不是标准 FDT),
我们的 `adtlib` 读不了 —— 但它可以 dump 成文本,本模块解析那个文本。

文本格式大致是缩进结构:

```
    arm-io {
        compatible = [arm-io,t8142]
        reg = [Container:
    addr = 0x0000000210F00000
    size = 0x0000000000002000, Container:
    addr = 0x0000000211F00000
    ...]
        ranges = [Container:
    bus_addr  = 0x0
    parent_addr = 0x210000000
    size = 0x3F000000, ...]
    }
```

## 关键用途

`arm-io` 的 `ranges` 给出**地址翻译窗口** ——
**物理地址 = 子地址 + window.parent_addr**(本机 J704 是 `0x2_1000_0000`)。

用法:
    python3 tools/adt_txt.py m5_adt.txt --ranges      # 只看翻译窗口
    python3 tools/adt_txt.py m5_adt.txt --list        # 列节点 + reg 首个地址
    python3 tools/adt_txt.py m5_adt.txt --tree        # 打印层级
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 节点: "<缩进><名字> {"
RE_NODE = re.compile(r"^(\s*)([A-Za-z0-9_@,.-]+)\s*\{\s*$")
# 属性: "<缩进>key = value"
RE_PROP = re.compile(r"^(\s*)([A-Za-z0-9_@,.#-]+)\s*=\s*(.*)$")
# Container 里的字段(缩进可能被打乱)
RE_FIELD = re.compile(r"^\s*(bus_addr|parent_addr|addr|size)\s*=\s*(0x[0-9a-fA-F]+)")


class Node:
    __slots__ = ("name", "props", "children", "depth")

    def __init__(self, name: str, depth: int):
        self.name = name
        self.depth = depth
        self.props: dict = {}      # key -> 原始字符串值
        self.children: list = []

    def __repr__(self) -> str:
        return "Node(%s, %d props, %d kids)" % (self.name, len(self.props), len(self.children))


def parse(path: str) -> Node:
    """把文本 dump 解析成节点树。"""
    root = Node("/", -1)
    stack = [root]
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        m = RE_NODE.match(line)
        if m:
            indent = len(m.group(1))
            node = Node(m.group(2), indent)
            while stack and stack[-1].depth >= indent:
                stack.pop()
            (stack[-1] if stack else root).children.append(node)
            stack.append(node)
            i += 1
            continue

        m = RE_PROP.match(line)
        if m and stack:
            key, val = m.group(2), m.group(3).strip()
            # 列表值:按**括号配平**吃后续行,不看缩进 ——
            # Container 的续行缩进比属性行还浅,按缩进判断会漏。
            if val.startswith("["):
                buf = [val]
                depth = val.count("[") - val.count("]")
                j = i + 1
                while depth > 0 and j < len(lines):
                    nxt = lines[j].strip()
                    buf.append(nxt)
                    depth += nxt.count("[") - nxt.count("]")
                    j += 1
                stack[-1].props[key] = " ".join(buf)
                i = j
                continue
            stack[-1].props[key] = val
        i += 1

    return root


def windows(root: Node) -> list:
    """从 arm-io 的 ranges 里取翻译窗口 [(bus_addr, parent_addr, size), ...]。"""
    out = []
    for n in walk(root):
        if n.name != "arm-io":
            continue
        raw = n.props.get("ranges")
        if not raw:
            continue
        # 按 Container 切段,每段取 bus_addr / parent_addr / size
        for seg in raw.split("Container"):
            vals = {}
            for m in re.finditer(r"(bus_addr|parent_addr|size)\s*=\s*(0x[0-9a-fA-F]+)", seg):
                vals[m.group(1)] = int(m.group(2), 16)
            if "bus_addr" in vals and "parent_addr" in vals:
                out.append((vals["bus_addr"], vals["parent_addr"], vals.get("size", 0)))
        break
    return out


def translate(addr: int, wins: list) -> int:
    """按窗口把子地址翻译成物理地址。"""
    for bus, parent, size in wins:
        if size and bus <= addr < bus + size:
            return addr - bus + parent
        if not size and addr == bus:
            return parent
    return addr


def first_reg_addr(node: Node) -> int | None:
    raw = node.props.get("reg")
    if not raw:
        return None
    m = re.search(r"addr\s*=\s*(0x[0-9a-fA-F]+)", raw)
    return int(m.group(1), 16) if m else None


def walk(node: Node):
    yield node
    for c in node.children:
        yield from walk(c)


def path_of(root: Node, target: Node) -> str:
    stack: list = []

    def rec(n) -> bool:
        stack.append(n)
        if n is target:
            return True
        for c in n.children:
            if rec(c):
                return True
        stack.pop()
        return False

    rec(root)
    return "/" + "/".join(x.name for x in stack[1:])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("txt", help="原始 ADT 的文本 dump")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ranges", action="store_true", help="只看地址翻译窗口")
    g.add_argument("--tree", action="store_true", help="打印层级树")
    g.add_argument("--memmap", action="store_true",
                   help="输出内存映射表(照官方 docs/hw/soc/memmap.md 的格式)")
    g.add_argument("--list", action="store_true", help="列节点 + 子地址 + 物理地址")
    args = ap.parse_args()

    if args.memmap:
        root = parse(args.txt)
        w = windows(root)
        rows = []
        for n in walk(root):
            a = first_reg_addr(n)
            if a is None:
                continue
            rows.append((translate(a, w), n))
        rows.sort(key=lambda r: r[0])
        print("     phys base        size  node")
        print("-" * 56)
        for phys, n in rows:
            size = 0
            for m in re.finditer(r"size\s*=\s*(0x[0-9a-fA-F]+)", n.props.get("reg", "")):
                size = int(m.group(1), 16)
                break
            print("0x%012x  0x%08x  %s" % (phys, size, path_of(root, n)))
        return 0

    root = parse(args.txt)

    if args.ranges:
        w = windows(root)
        if not w:
            print("没找到 arm-io 的 ranges", file=sys.stderr)
            return 1
        print("arm-io 地址翻译窗口:")
        for bus, parent, size in w:
            d = parent - bus
            print("  bus 0x%-11x -> phys 0x%-11x size 0x%-9x  Δ=0x%x" % (bus, parent, size, d))
        return 0

    if args.tree:
        for n in walk(root):
            print("  " * (n.depth // 4) + n.name)
        return 0

    w = windows(root)
    nodes = [n for n in walk(root) if first_reg_addr(n) is not None]
    print("节点总数: %d   带 reg 的: %d   翻译窗口: %d" % (len(list(walk(root))), len(nodes), len(w)))
    print()
    print("%-34s %-14s %-14s %s" % ("路径", "子地址", "物理地址", "compatible"))
    print("-" * 90)
    for n in nodes:
        a = first_reg_addr(n)
        comp = n.props.get("compatible", "")
        comp = comp.strip("[]")[:34] if comp else ""
        print("%-34s 0x%-11x 0x%-11x %s" % (path_of(root, n)[:34], a, translate(a, w), comp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
