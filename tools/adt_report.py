#!/usr/bin/env python3
"""从 ADT 生成一份可读的硬件清单(markdown)。

用途:把机器可读的 dump 变成人能扫的表,便于和 M4 的 dtsi 逐块对照。

用法:
    python3 tools/adt_report.py ~/m5-adt.plist -o docs/INVENTORY.md
    python3 tools/adt_report.py ~/m5-adt.plist --prefix /arm-io

只输出 name / compatible / device_type / reg —— 不含任何序列号类字段。
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adtlib  # noqa: E402
from adt2dts import iter_paths, select  # noqa: E402


def build(root, prefix: str | None, src_name: str) -> str:
    keep = select(root, prefix, ancestors=False)

    total = 0
    with_compat = 0
    families: Counter = Counter()
    family_example: dict = {}
    rows: list = []

    for node, path in iter_paths(root):
        if prefix is not None and keep is not None and id(node) not in keep:
            continue
        total += 1
        comps = node.compatible
        if not comps:
            continue
        with_compat += 1
        c = comps[0]
        fam = c.split(",")[0] if "," in c else c
        families[fam] += 1
        family_example.setdefault(fam, node.name)
        rows.append((
            c,
            node.name,
            node.unit_addr or "",
            node.device_type or "",
            path,
        ))

    rows.sort(key=lambda r: (r[0], r[1]))
    out = [
        "# 硬件清单",
        "",
        "- 来源: `%s`" % src_name,
        "- 生成日期: %s" % date.today().isoformat(),
        "- 节点总数: **%d**,其中带 `compatible` 的 **%d**" % (total, with_compat),
        "",
        "> ⚠️ 若来源是 `ioreg` dump,这是 **macOS 过滤视图**,不是原始 ADT。",
        "> 每个块的语义以原始 ADT + 真机实测为准。来源纪律见 `docs/PROVENANCE.md`。",
        "",
        "## 1 按设备块族统计",
        "",
        "| 族 | 节点数 | 例子 |",
        "|---|---:|---|",
    ]
    for fam, n in families.most_common():
        out.append("| `%s` | %d | `%s` |" % (fam, n, family_example[fam]))

    out += [
        "",
        "## 2 完整清单",
        "",
        "| compatible | 节点 | 单元地址 | device_type | 路径 |",
        "|---|---|---|---|---|",
    ]
    for c, name, addr, dt, path in rows:
        out.append("| `%s` | `%s` | `%s` | %s | `%s` |" % (c, name, addr, dt, path))

    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("adt", help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("--prefix", help="只统计该子树")
    ap.add_argument("-o", "--out", help="输出文件(默认 stdout)")
    args = ap.parse_args()

    root = adtlib.load(args.adt)
    text = build(root, args.prefix, Path(args.adt).name)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("已写入 %s(%d 行)" % (args.out, text.count("\n")), file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
