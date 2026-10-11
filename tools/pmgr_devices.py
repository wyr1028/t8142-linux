#!/usr/bin/env python3
"""解码 PMGR 的 `devices` 属性。

## 结构(从 blob 本身推出,见 docs/PMGR-DEVICES.md)

- **定长 48 字节 × N 条**,N = len(blob) / 48
  本机:387 条 × 48 = 18576 = blob 长度,精确吻合
- 每条**偏移 32 处**是 16 字节的 NUL 结尾名字
- 数值字段**小端**

## 已知的字段(名字前的 32 字节)

| 偏移 | 宽度 | 观察 |
|---|---|---|
| **0** | 1 | **flags**。`0x10` = 虚拟域(无真实寄存器) |
| 12 | 4 | 小端计数,逐条 +1 |
| **16** | **3+1** | **寄存器偏移(已确证,见下)** + 8 位 group,本机 `{0,1,2}` |
| 26 | 2 | 小端设备号,范围 1..561 且稀疏 |
| 20, 28 | 4 | 本机全为 0 |
| 4, 8, 24 | — | 取值较多,语义未定 |

### 偏移字段在 16 的**确证过程**

拿 M4 模板里那 8 个"两边偏移恰好相同"的条目做定位实验 ——
把 M4 已知的偏移值去 M5 记录的每个字段里找:

```
gpio/sep/venc_dma/venc_pipe4/5/me0/me1/disp_cpu   → 全部命中 u32@16   8/8
```

8 个全中,没有例外,所以**偏移在 u32@16 这一条是确定的**,不是猜的。

⚠️ **偏移在 u32@16 已确证**(8/8 定位实验,见下),其余字段语义未定。
**注意:387 条里有 86 条偏移为 0** —— 说明绝对地址还要一个基址,详见
[docs/PMGR-DEVICES.md](../docs/PMGR-DEVICES.md) 第 4 节。节点地址会撞车,
不能直接拿来当 DTS 的 `reg`。

## 来源诚实说明

**本项目作者在与 AI 的同一会话中,曾接触过上游 m1n1 仓库的 `src/pmgr.c` 片段
(前 135 行)。** 上面的 48 字节结构是从 blob 独立推出的,但字段解释**可能受到
那段内容的提示**,不能声称是纯黑盒结果。详见 docs/PROVENANCE.md。

用法:
    python3 tools/pmgr_devices.py ~/m5-adt.plist
    python3 tools/pmgr_devices.py ~/m5-adt.plist --tsv
    python3 tools/pmgr_devices.py --blob raw-devices.bin
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adtlib  # noqa: E402

RECORD_SIZE = 48
NAME_OFFSET = 32
NAME_LEN = 16


def parse(blob: bytes) -> list:
    """blob -> [{index, name, raw, fields}, ...]。"""
    if len(blob) % RECORD_SIZE:
        raise ValueError("长度 %d 不是 %d 的整数倍,结构可能不是定长 48"
                         % (len(blob), RECORD_SIZE))
    recs = []
    for i in range(len(blob) // RECORD_SIZE):
        r = blob[i * RECORD_SIZE:(i + 1) * RECORD_SIZE]
        name = r[NAME_OFFSET:NAME_OFFSET + NAME_LEN].split(b"\x00")[0].decode("ascii", "replace")
        recs.append({
            "index": i,
            "name": name,
            "raw": r[:NAME_OFFSET],
            # 几个已观察到的字段,便于筛选与排序
            # 字节 0 是 flags:0x10 = 虚拟域(无真实寄存器)
            "flags": r[0],
            "virtual": bool(r[0] & 0x10),
            "f00": struct.unpack_from("<I", r, 0)[0],
            "f12": struct.unpack_from("<I", r, 12)[0],
            "f16": struct.unpack_from("<I", r, 16)[0],
            "f16_group": r[19],
            "f16_offset": int.from_bytes(r[16:19], "little"),
            "id": struct.unpack_from("<H", r, 26)[0],
        })
    return recs


def get_devices(adt_path: str, node: str = "pmgr") -> bytes:
    root = adtlib.load(adt_path)
    for n in root.find(node):
        v = n.props.get("devices")
        if isinstance(v, (bytes, bytearray)):
            return bytes(v)
    raise LookupError("在 %s 里没找到 %s 节点的 devices 属性" % (adt_path, node))


def show_ps_groups(adt_path: str, node: str = "pmgr") -> int:
    """打印 `ps-groups`(基址索引表)与 pmgr 的 `reg`。

    设备记录里的 group 字段索引这张表,拿到 (reg_idx, reg_offset),
    再去 pmgr 的 `reg` 属性里取第 reg_idx 条地址 —— 这就是**基址**。

    ⚠️ `reg` 的 cell 划分没定论:本机 864 字节,按 2 cell 解是 108 条、
    按 4 cell 解是 54 条,两种解出的第一个地址都含 0x70700000(pmgr 自己的
    节点地址),所以还没法靠数据分辨。需要真机或父节点的 #address-cells。
    """
    root = adtlib.load(adt_path)
    p = next(root.find(node))

    g = p.props.get("ps-groups")
    if not isinstance(g, (bytes, bytearray)) or len(g) % 12:
        print("没找到形状正确的 ps-groups", file=sys.stderr)
        return 1

    print("ps-groups(%d 字节,%d 组):" % (len(g), len(g) // 12))
    for i in range(len(g) // 12):
        a, b, c = struct.unpack_from("<III", g, i * 12)
        print("  group %d:  reg_idx=%-4d reg_offset=0x%-6x unk=0x%x" % (i, a, b, c))

    r = p.props.get("reg")
    if isinstance(r, (bytes, bytearray)):
        print()
        print("pmgr reg(%d 字节):" % len(r))
        for cells in (2, 4):
            print("  按 %d cell/条 解 -> %d 条" % (cells, len(r) // (cells * 4)))
        print("  前 4 条的原始 cell(小端 u32):")
        for i in range(0, min(len(r), 64), 4):
            print("    [%2d] 0x%08x" % (i // 4, struct.unpack_from("<I", r, i)[0]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("adt", nargs="?", help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("--blob", help="直接给 devices 二进制文件")
    ap.add_argument("--tsv", action="store_true", help="TSV 输出")
    ap.add_argument("--ps-groups", action="store_true",
                    help="打印 ps-groups(基址索引表)与 pmgr reg,不解 devices")
    args = ap.parse_args()

    if args.ps_groups:
        if not args.adt:
            ap.error("--ps-groups 需要 adt")
        return show_ps_groups(args.adt)

    if args.blob:
        blob = Path(args.blob).read_bytes()
    elif args.adt:
        blob = get_devices(args.adt)
    else:
        ap.error("要给 adt 或 --blob 之一")

    recs = parse(blob)

    if args.tsv:
        print("index\tname\tid\tf00\tf12\tf16\tgroup\tf16_offset\traw32")
        for r in recs:
            print("%d\t%s\t%d\t0x%08x\t%d\t%d\t%d\t%d\t%s" % (
                r["index"], r["name"], r["id"], r["f00"], r["f12"],
                r["f16"], r["f16_group"], r["f16_offset"], r["raw"].hex()))
    else:
        named = [r for r in recs if r["name"]]
        print("记录数: %d(48 字节 × %d = %d)"
              % (len(recs), len(recs), len(recs) * RECORD_SIZE))
        print("有名字的: %d,无名字的: %d" % (len(named), len(recs) - len(named)))
        print()
        print("| # | 名字 | id | f00 | f12 | f16 | group | off |")
        print("|---:|---|---:|---|---:|---:|---:|---:|")
        for r in recs:
            print("| %d | `%s` | %d | `0x%04x` | %d | %d | %d | %d |" % (
                r["index"], r["name"], r["id"], r["f00"], r["f12"],
                r["f16"], r["f16_group"], r["f16_offset"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
