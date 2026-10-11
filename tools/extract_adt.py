#!/usr/bin/env python3
"""从**本机 macOS** 里提取原始 ADT —— 不需要 m1n1、不需要 tethered boot。

## 原理

macOS 的 Preboot 卷里存着固件发布时的设备树:

    /System/Volumes/Preboot/<UUID>/restore/Firmware/all_flash/DeviceTree.<board>.im4p

那是个 **ASN.1 DER** 容器:

```
30 82 xx xx                          SEQUENCE
  16 04  "IM4P"                      magic
  16 04  "dtre"                      类型: DeviceTree
  16 xx  "EmbeddedDeviceTrees-…"     版本
  04 82 xx xx  <payload>             OCTET STRING,LZFSE 压缩(bvx2)
  30 08 …                            (尾部小结构)
```

解出 OCTET STRING、LZFSE 解压,就是**原始 ADT 二进制**。

> ⚠️ 这是 **iBoot 之前**的版本 —— 官方文档说它
> "missing details filled in by iBoot during boot"。
> 想要 100% 完整的,仍然要 m1n1 从真机 dump。

## 用法

    python3 tools/extract_adt.py                    # 自动找本机的
    python3 tools/extract_adt.py --list             # 只列出找到的文件
    python3 tools/extract_adt.py -o raw-adt.bin     # 指定输出

**解码**(Apple 私有 ADT 格式,魔数 `0x17`)要 m1n1 自带的工具:

    cd m1n1/proxyclient && python3 -m m1n1.adt raw-adt.bin > adt.txt

## 来源与合规

读的是**你自己机器上 macOS 自带**的文件,不是泄露资料 —— 见 docs/LEGAL.md。
**本工具只提取、不解密、不绕过任何保护**(payload 是 LZFSE 压缩,未加密)。
"""

from __future__ import annotations

import argparse
import ctypes
import struct
import sys
from pathlib import Path

PREBOOT = Path("/System/Volumes/Preboot")
_GLOB = "*/restore/Firmware/all_flash/DeviceTree.*.im4p"


def find_im4p() -> list:
    return sorted(PREBOOT.glob(_GLOB))


def der_tlv(b: bytes, i: int):
    tag = b[i]
    i += 1
    ln = b[i]
    i += 1
    if ln & 0x80:
        n = ln & 0x7F
        ln = int.from_bytes(b[i:i + n], "big")
        i += n
    return tag, ln, i


def parse_im4p(data: bytes) -> dict:
    """极简 DER 走一遍。返回 {magic, type, version, payload}。"""
    tag, ln, i = der_tlv(data, 0)
    if tag != 0x30:
        raise ValueError("顶层不是 SEQUENCE(tag=0x%02x)" % tag)
    seq = data[i:i + ln]

    out = {"fields": []}
    j = 0
    while j < len(seq):
        t, l, k = der_tlv(seq, j)
        v = seq[k:k + l]
        out["fields"].append((t, v))
        if t == 0x16 and out.get("magic") is None:
            out["magic"] = v.decode("ascii", "replace")
        elif t == 0x16 and out.get("type") is None:
            out["type"] = v.decode("ascii", "replace")
        elif t == 0x16 and out.get("version") is None:
            out["version"] = v.decode("ascii", "replace")
        elif t == 0x04 and out.get("payload") is None:
            out["payload"] = v
        j = k + l
    return out


def lzfse_decompress(payload: bytes, cap: int = 16 * 1024 * 1024) -> bytes:
    """用 macOS 自带的 libcompression 解 LZFSE。"""
    lib = ctypes.CDLL("/usr/lib/libcompression.dylib")
    lib.compression_decode_buffer.restype = ctypes.c_size_t
    dst = ctypes.create_string_buffer(cap)
    n = lib.compression_decode_buffer(dst, cap, payload, len(payload), None, 0x801)  # LZFSE
    if n == 0:
        raise RuntimeError("LZFSE 解压失败(输出可能超过 %d 字节)" % cap)
    return dst.raw[:n]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", help="输出的 .bin 路径(默认 raw-adt.bin)")
    ap.add_argument("--list", action="store_true", help="只列出找到的 im4p")
    args = ap.parse_args()

    files = find_im4p()
    if not files:
        print("在 %s 下没找到 DeviceTree.*.im4p" % PREBOOT, file=sys.stderr)
        print("提示:可能需要给终端完全磁盘访问权限。", file=sys.stderr)
        return 1

    if args.list:
        for f in files:
            print("  %s  (%d 字节)" % (f, f.stat().st_size))
        return 0

    if len(files) > 1:
        print("找到 %d 个,取第一个:" % len(files), file=sys.stderr)
    src = files[0]
    print("来源: %s" % src)

    info = parse_im4p(src.read_bytes())
    print("  magic   : %s" % info.get("magic"))
    print("  type    : %s" % info.get("type"))
    print("  版本    : %s" % info.get("version"))
    pl = info.get("payload")
    if not pl:
        print("没找到 OCTET STRING payload", file=sys.stderr)
        return 1
    print("  payload : %d 字节(压缩)" % len(pl))

    raw = lzfse_decompress(pl)
    print("  解压后  : %d 字节" % len(raw))

    # ADT 是**小端**:首 4 字节 17 00 00 00 -> 0x17
    magic = struct.unpack("<I", raw[:4])[0]
    print("  ADT 魔数: 0x%x%s" % (magic, "  ✓" if magic == 0x17 else "  ⚠️ 与预期的 0x17 不同"))

    out = Path(args.out or "raw-adt.bin")
    out.write_bytes(raw)
    print("\n已写入 %s" % out)
    print("下一步解码(用 m1n1 自带的工具):")
    print("  cd m1n1/proxyclient && python3 -m m1n1.adt %s > adt.txt" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
