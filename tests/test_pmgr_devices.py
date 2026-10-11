#!/usr/bin/env python3
"""pmgr_devices 自测。

用**合成 blob** 验证结构假设(定长 48、名字在 +32、小端),不依赖真机数据。

跑:
    python3 tests/test_pmgr_devices.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import pmgr_devices as P  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print("  ok  %s" % msg)


def synth(entries) -> bytes:
    """entries: [(name, f00, f12, off, group, devid)]"""
    out = bytearray()
    for name, f00, f12, off, group, devid in entries:
        rec = bytearray(48)
        struct.pack_into("<I", rec, 0, f00)
        struct.pack_into("<I", rec, 12, f12)
        rec[16:19] = off.to_bytes(3, "little")
        rec[19] = group
        struct.pack_into("<H", rec, 26, devid)
        nb = name.encode()
        rec[32:32 + len(nb)] = nb
        out += rec
    return bytes(out)


def test_parse() -> None:
    print("[parse] 合成 blob")
    blob = synth([
        ("ECPU_0", 0x20000, 1, 0, 0, 1),
        ("ECPU_1", 0x20000, 2, 8, 0, 2),
        ("ECPM", 0x3020000, 0, 80, 1, 11),
    ])
    recs = P.parse(blob)
    check(len(recs) == 3, "条数 = 3")
    check(recs[0]["name"] == "ECPU_0", "名字解码")
    check(recs[2]["name"] == "ECPM", "第三条名字")
    check(recs[1]["f16_offset"] == 8, "偏移字段 = 8")
    check(recs[2]["f16_group"] == 1, "group = 1")
    check(recs[2]["id"] == 11, "设备号 = 11")
    check(recs[1]["f12"] == 2, "f12 小端解码")
    check(len(recs[2]["raw"]) == 32, "raw 取名字前的 32 字节")


def test_bad_length() -> None:
    print("[parse] 长度不是 48 的倍数要报错")
    try:
        P.parse(b"\x00" * 47)
    except ValueError as e:
        check("48" in str(e), "抛出 ValueError: %s" % e)
    else:
        raise AssertionError("竟然没报错")


def test_name_boundary() -> None:
    print("[parse] 名字占满 16 字节(无 NUL 结尾)")
    rec = bytearray(48)
    rec[32:48] = b"A" * 16
    recs = P.parse(bytes(rec))
    check(recs[0]["name"] == "A" * 16, "16 字节名字不被截断")


def test_empty_name() -> None:
    print("[parse] 空名字")
    recs = P.parse(bytes(48))
    check(recs[0]["name"] == "", "空名字返回空串")


def main() -> int:
    for fn in (test_parse, test_bad_length, test_name_boundary, test_empty_name):
        fn()
        print()
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
