#!/usr/bin/env python3
"""把 M4 的 PMGR **结构** + M5 的 **偏移** 合成一份 `t8142-pmgr.dtsi` 草稿。

依据见 [docs/PMGR-DELTA.md]:两边的设备名 92% 重合,但偏移只有 6% 相同 ——
所以正确做法是**按名字 join**,结构抄 M4、数值用 M5。

## 产出是草稿,不是成品

必须:
1. **人工校对** —— 名字对不上不等于设备没了;M4 只写了 129 条而 ADT 有 485 个设备,
   说明上游做过**筛选**,筛选口径本工具不知道
2. **真机验证** —— 偏移来自 macOS 过滤视图

## 用法

    python3 tools/pmgr_join.py \\
        --template t8132-pmgr.dtsi \\
        --adt ~/m5-adt.plist \\
        -o dts/t8142-pmgr.dtsi

模板从哪来:`AsahiLinux/linux`(分支 `asahi`)
`arch/arm64/boot/dts/apple/t8132-pmgr.dtsi`。**不纳入本仓库**,用参数传。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pmgr_devices as P  # noqa: E402

# M4 模板里一条 power-controller 的形态
RE_ENTRY = re.compile(r"power-controller@([0-9a-fA-F]+)\s*\{(.*?)\n\t\};", re.S)
RE_LABEL = re.compile(r'label = "([^"]+)"')
RE_COMPAT = re.compile(r'compatible = "([^"]+)"')
RE_CELLS = re.compile(r"#(power-domain|reset)-cells = <(\d+)>")

# 我们生成时统一用的 SoC 兼容串
OUR_COMPAT = '"apple,t8142-pmgr-pwrstate", "apple,t8103-pmgr-pwrstate"'


def parse_template(path: str):
    """M4 dtsi -> {小写label: {offset, flags, cells}}。"""
    txt = Path(path).read_text(encoding="utf-8")
    out = {}
    for m in RE_ENTRY.finditer(txt):
        off = int(m.group(1), 16)
        body = m.group(2)
        lm = RE_LABEL.search(body)
        if not lm:
            continue
        label = lm.group(1)
        cells = {k: int(v) for k, v in RE_CELLS.findall(body)}
        out[label.lower()] = {
            "offset": off,
            "label": label,
            "always_on": "apple,always-on" in body,
            "pdc": cells.get("power-domain", 0),
            "rc": cells.get("reset", 0),
        }
    return out


def sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def emit(template: dict, m5: list, tpl_name: str, tpl_hash: str) -> str:
    from collections import Counter

    # 虚拟域(flags & 0x10)没有真实寄存器,不进 DTS
    real = [r for r in m5 if not r["virtual"]]
    virt = [r for r in m5 if r["virtual"]]

    cnt = Counter(r["f16_offset"] for r in real)
    unique = sorted((r for r in real if cnt[r["f16_offset"]] == 1),
                    key=lambda x: x["f16_offset"])
    dup = sorted((r for r in real if cnt[r["f16_offset"]] > 1),
                 key=lambda x: (x["f16_offset"], x["name"]))

    matched = [r for r in unique if r["name"].lower() in template]
    del matched  # 只在下面表头里用,保留计算是为了将来扩展

    L = [
        "// SPDX-License-Identifier: GPL-2.0-or-later",
        "/*",
        " * PMGR Power domains for the Apple T8142 \"M5\" SoC — 草稿",
        " *",
        " * 由 tools/pmgr_join.py 生成,输入:",
        " *   模板: %s  (sha256 %s)" % (tpl_name, tpl_hash),
        " *       上游 AsahiLinux/linux, arch/arm64/boot/dts/apple/t8132-pmgr.dtsi",
        " *   数值: 本机 ADT 的 pmgr `devices` 属性(387 条)",
        " * 生成日期: %s" % date.today().isoformat(),
        " *",
        " * ⚠️ 草稿。必须人工校对 + 真机验证。见 docs/PMGR-DELTA.md。",
        " *",
        " * 记录 %d 条:非虚拟 %d 条,其中偏移唯一、写出为节点的 %d 条。"
        % (len(m5), len(real), len(unique)),
        " *",
        " * 地址结构:**绝对地址 = base(group) + offset**",
        " *   base 由 pmgr 的 ps-groups 表索引 reg 属性得到,本机三组分别是",
        " *   0x170700000 / 0x178280000 / 0x370e80000。",
        " *",
        " * 未写出的(%d 条偏移仍不唯一 + %d 条虚拟域)见文件末尾两个注释块。" % (len(dup), len(virt)),
        " */",
        "",
        "&pmgr {",
        "",
    ]

    for r in unique:
        key = r["name"].lower()
        label = key.replace("-", "_")
        off = r["f16_offset"]
        virt = " /* 虚拟域:flags 有 0x10,可能没有真实寄存器 */" if r["virtual"] else ""
        if key in template:
            t = template[key]
            L.append("\tps_%s: power-controller@%x {%s" % (label, off, virt))
            L.append("\t\tcompatible = %s;" % OUR_COMPAT)
            L.append("\t\treg = <%#x 4>;" % off)
            L.append("\t\t#power-domain-cells = <%d>;" % t["pdc"])
            L.append("\t\t#reset-cells = <%d>;" % t["rc"])
            L.append('\t\tlabel = "%s";  /* 结构抄自 M4 模板同名项 */' % t["label"])
            if t["always_on"]:
                L.append("\t\tapple,always-on; /* Core device */")
            L.append("\t};")
        else:
            L.append("\t/* ⚠️ M4 模板里没有同名项 —— 下面属性是猜的,需确认 */")
            L.append("\tps_%s: power-controller@%x {%s" % (label, off, virt))
            L.append("\t\tcompatible = %s;" % OUR_COMPAT)
            L.append("\t\treg = <%#x 4>;" % off)
            L.append("\t\t#power-domain-cells = <0>;")
            L.append("\t\t#reset-cells = <0>;")
            L.append('\t\tlabel = "%s";' % key)
            L.append("\t};")
        L.append("")

    L += ["};", ""]

    if dup:
        L += [
            "/*",
            " * ====== 未写出:偏移在非虚拟域里仍不唯一(%d 条)======" % len(dup),
            " *",
            " * 绝对地址 = base(group) + offset,base 来自 pmgr 的 ps-groups × reg。",
            " * 这几条的 (group, offset) 不同但 offset 相同,而 DT 的节点名单元地址",
            " * 用的是 offset(M4 的写法),会撞车。等定清 pmgr 的 ranges 怎么表达多基址再说。",
            " * 格式: offset  group  id  名字",
            " *",
        ]
        for r in dup:
            L.append(" *  0x%05x  g=%d  id=%-4d  %s"
                     % (r["f16_offset"], r["f16_group"], r["id"], r["name"]))
        L += [" */", ""]

    L += [
        "/*",
        " * ====== 虚拟域(flags 带 0x10),本文件不处理(%d 条)======" % len(virt),
        " *",
        " * 这些没有真实寄存器,是 PMGR 合成的状态域。是否需要在 DTS 里表达、",
        " * 以及怎么表达,未知 —— 上游 M4 的 dtsi 里也没有对应写法可参考。",
        " * 格式: offset  group  id  名字",
        " *",
    ]
    for r in virt:
        L.append(" *  0x%05x  g=%d  id=%-4d  %s"
                 % (r["f16_offset"], r["f16_group"], r["id"], r["name"]))
    L += [" */", ""]

    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", required=True, help="M4 的 t8132-pmgr.dtsi")
    ap.add_argument("--adt", required=True, help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("-o", "--out", help="输出文件(默认 stdout)")
    args = ap.parse_args()

    template = parse_template(args.template)
    if not template:
        print("模板里没解析出条目,检查是不是 t8132-pmgr.dtsi", file=sys.stderr)
        return 1

    blob = P.get_devices(args.adt)
    m5 = P.parse(blob)

    text = emit(template, m5, Path(args.template).name, sha256(args.template))

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print("已写入 %s(%d 行)" % (args.out, text.count("\n")), file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
