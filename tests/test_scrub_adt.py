#!/usr/bin/env python3
"""scrub_adt 自测。

覆盖两个踩过的坑:
1. **值为空的属性**会 IndexError(构造 scrub 时 `as_str_list(v)[0]`)
2. **文本自查误报** —— 节点名、以及值里连续 NUL 渲染出的双空格,会被当成敏感字段

跑:
    python3 tests/test_scrub_adt.py
"""

from __future__ import annotations

import plistlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import adtlib  # noqa: E402
import scrub_adt as S  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print("  ok  %s" % msg)


def make_plist() -> str:
    root = {
        "IORegistryEntryName": "Root",
        "serial-number": b"ABC123XYZ",
        "uid-aes-key": b"\x00" * 16,
        "IORegistryEntryChildren": [
            {
                "IORegistryEntryName": "thing",
                "compatible": b"test,thing\x00",
                "device_type": b"",          # ← 空值:曾经在这里 IndexError
                "reg": b"\x00\x00\x10\x00\x00\x00\x00\x10",
            },
            {"IORegistryEntryName": "InvalidateHmac"},   # ← 名字里含敏感词
        ],
    }
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".plist")
    plistlib.dump(root, f)
    f.close()
    return f.name


def test_is_sensitive() -> None:
    print("[is_sensitive]")
    for k in ("serial-number", "UUID", "local-mac-address", "SEPApNonce", "uid-aes-key"):
        check(S.is_sensitive(k), "%s 判为敏感" % k)
    for k in ("compatible", "device_type", "reg", "name", "clock-ids"):
        check(not S.is_sensitive(k), "%s 判为非敏感" % k)


def test_scrub_drops_secrets() -> None:
    print("[scrub] 空值不崩 + 敏感字段不落盘")
    p = make_plist()
    try:
        text = S.scrub(adtlib.load(p), S.DEFAULT_KEEP)
        check("ABC123XYZ" not in text, "序列号的值没出现")
        check("serial-number" not in text, "序列号的键没出现")
        check("uid-aes-key" not in text, "密钥键没出现")
        check("compatible=test,thing" in text, "compatible 正常输出")
        check("reg=[" in text, "reg 正常输出")
        check("thing" in text, "空值节点没被丢掉")
    finally:
        Path(p).unlink()


def test_text_scanner_no_false_positive() -> None:
    print("[verify_text] 不误报节点名 / 碎片")
    d = Path(tempfile.mkdtemp())
    try:
        f = d / "topo.txt"
        f.write_text(
            "# 注释里有 serial-number 也不算\n"
            "/Root/InvalidateHmac\n"                      # 纯节点名,无属性
            "/Root/x   compatible=a,b  ok=1\n"            # 正常
            "/Root/y   compatible=  InvalidateHmac\n"     # 值里双空格切出的碎片
        )
        check(S.verify_text(str(f)) == 0, "没有真属性 → 判干净")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def test_text_scanner_catches_real() -> None:
    print("[verify_text] 真敏感字段要抓到")
    d = Path(tempfile.mkdtemp())
    try:
        f = d / "bad.txt"
        f.write_text("/x   serial-number=ABC123  uuid=deadbeef\n")
        check(S.verify_text(str(f)) == 1, "抓到并返回 1")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def test_verify_on_atd() -> None:
    print("[verify] 对 ADT 输入直接查")
    p = make_plist()
    try:
        check(S.verify(p) == 1, "含敏感字段的 dump → 返回 1")
    finally:
        Path(p).unlink()


def main() -> int:
    for fn in (test_is_sensitive, test_scrub_drops_secrets,
               test_text_scanner_no_false_positive, test_text_scanner_catches_real,
               test_verify_on_atd):
        fn()
        print()
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
