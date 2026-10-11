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
| 0 | 4 | 同族设备相同,换族会变(ECPU_* = `00000200`,PCPU_* = `00000500`) |
| 12 | 4 | 小端计数,逐条 +1 |
| 16 | 4 | 小端,ECPU_0..5 上是 0,8,16,24,32,40 —— 步长 8 |
| 26 | 2 | 小端,1 起递增,恰等于记录序号 + 1 |
| 20, 28 | 4 | 本机全为 0 |
| 4, 8, 24 | — | 取值较多,语义未定 |

⚠️ **语义未完全确定。** 本工具只保证**结构**解对了(有 387×48 这个精确锚点),
字段含义标为"观察"而非"已知"。要确定语义,需要在真机上做读写实验。

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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("adt", nargs="?", help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("--blob", help="直接给 devices 二进制文件")
    ap.add_argument("--tsv", action="store_true", help="TSV 输出")
    args = ap.parse_args()

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
