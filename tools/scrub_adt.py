#!/usr/bin/env python3
"""把 ADT / ioreg dump 洗成**可安全外发**的形式,并在发布前自查。

原始 dump 里有:序列号、UUID、MAC、`uid-aes-key`、`SEPApNonce` 等。
`.gitignore` 只挡得住 `git add -A`,**挡不住手动 `git add -f`** ——
所以外发前必须过一遍工具,而不是靠记性。

## 两个模式

    # 生成只含结构的版本(默认只留 name / compatible / device_type / reg)
    python3 tools/scrub_adt.py ~/m5-adt.plist -o ~/m5-adt-topology.txt

    # 发布前自查:某个文件里有没有敏感字段(有则退出码 1)
    python3 tools/scrub_adt.py --verify ~/m5-adt-topology.txt

## 为什么默认只留四个键

白名单比黑名单可靠:**想不到的敏感键不会被漏掉**,因为它们本来就不在白名单里。
要用别的键,显式 `--keep`。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adtlib  # noqa: E402

# 敏感键的**子串**(小写匹配)。宁可多判,不可漏判。
SENSITIVE = (
    "serial", "uuid", "udid", "mac-address", "nonce", "aes-key", "keybag",
    "ecid", "msid", "gsid", "hmac", "seal-key", "manifest-hash", "boot-nonce",
    "apnonce", "chip-id", "board-id", "target-type", "region-info",
)

DEFAULT_KEEP = {"name", "compatible", "device_type", "reg"}


def is_sensitive(key: str) -> bool:
    kl = key.lower()
    return any(s in kl for s in SENSITIVE)


def walk_with_path(node, path=""):
    cur = path + "/" + node.name
    yield node, cur
    for c in node.children:
        yield from walk_with_path(c, cur)


SEP = "   "  # 路径与属性之间的分隔;--verify 靠它把"节点名"和"属性"分开


def scrub(root, keep: set) -> str:
    lines = []
    for node, path in walk_with_path(root):
        bits = []
        for k in sorted(keep):
            if k not in node.props:
                continue
            v = node.props[k]

            if k == "compatible":
                cs = adtlib.as_str_list(v)
                if cs:
                    bits.append("compatible=%s" % ",".join(cs))
            elif k == "reg":
                cells = adtlib.reg_cells(v)
                if cells:
                    bits.append("reg=[%s]" % " ".join(cells))
            elif isinstance(v, (bytes, bytearray)):
                sl = adtlib.as_str_list(v)
                if sl:  # 空值跳过 —— 否则会 IndexError
                    bits.append("%s=%s" % (k, sl[0]))
            else:
                bits.append("%s=%s" % (k, v))

        lines.append(path + (SEP + "  ".join(bits) if bits else ""))
    return "\n".join(lines) + "\n"


def verify_text(path: str) -> int:
    """不是 ADT 时退化成原文扫描(例如查刚洗出来的拓扑文本)。

    只查**属性位置**(`key=value` 里的 key),不查节点名 ——
    否则 `InvalidateHmac`、`serial-device` 这类**节点名**会被误报。
    """
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        print("读不了 %s: %s" % (path, e), file=sys.stderr)
        return 2

    hits = set()
    for line in raw.splitlines():
        if line.startswith("#") or SEP not in line:
            continue  # 注释行、没有属性的行(纯节点名)跳过
        _, _, props = line.partition(SEP)
        for kv in props.split("  "):
            if "=" not in kv:
                continue  # 没有等号的不算属性 —— 挡掉值里连续 NUL 渲染成双空格切出的碎片
            key = kv.split("=", 1)[0].strip().lower()
            if key and is_sensitive(key):
                hits.add(key)

    if hits:
        print("属性位置出现敏感字段:%s" % ", ".join(sorted(hits)))
        return 1
    print("干净:没发现敏感字段")
    return 0


def verify(path: str) -> int:
    """扫描一个 ADT/plist 文件,报告敏感键。返回 0 表示干净。"""
    try:
        root = adtlib.load(path)
    except Exception:
        return verify_text(path)

    hits = []
    for node, _ in walk_with_path(root):
        for k in node.props:
            if is_sensitive(k):
                hits.append((k, node.name))
    if hits:
        print("发现 %d 处敏感字段:" % len(hits))
        seen = set()
        for k, n in hits:
            if k not in seen:
                seen.add(k)
                print("   %-24s 例:%s" % (k, n))
        return 1
    print("干净:没发现敏感字段")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="ADT 输入(ioreg plist 或 FDT blob)")
    ap.add_argument("-o", "--out", help="输出文件(默认 stdout)")
    ap.add_argument("--verify", action="store_true",
                    help="只检查敏感字段,不生成(有敏感字段则退出码 1)")
    ap.add_argument("--keep", action="append", default=[],
                    help="额外保留的键,可重复;默认只保留 name/compatible/device_type/reg")
    args = ap.parse_args()

    if args.verify:
        return verify(args.input)

    root = adtlib.load(args.input)
    keep = DEFAULT_KEEP | set(args.keep)
    text = scrub(root, keep)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("已写入 %s(%d 行)" % (args.out, text.count("\n")), file=sys.stderr)
    else:
        sys.stdout.write(text)

    # 顺手自检:刚生成的东西不该再有敏感字段
    bad = [k for k in keep if is_sensitive(k)]
    if bad:
        print("⚠️ --keep 里含敏感键:%s" % ", ".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
