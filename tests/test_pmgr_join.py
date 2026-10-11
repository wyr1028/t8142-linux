#!/usr/bin/env python3
"""pmgr_join 自测。

最重要的一条:**生成的 dtsi 里不能有重复的节点地址** ——
否则 DTS 编不过(这是实际踩过的坑:387 条里有 132 条偏移重复)。

跑:
    python3 tests/test_pmgr_join.py
"""

from __future__ import annotations

import re
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import pmgr_devices as P  # noqa: E402
import pmgr_join as J  # noqa: E402

TEMPLATE = """// SPDX-License-Identifier: GPL-2.0+ OR MIT
&pmgr {
	ps_aic: power-controller@110 {
		compatible = "apple,t8132-pmgr-pwrstate", "apple,t8103-pmgr-pwrstate";
		reg = <0x110 4>;
		#power-domain-cells = <0>;
		#reset-cells = <0>;
		label = "aic";
		apple,always-on; /* Core device */
	};
};
"""


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print("  ok  %s" % msg)


def synth(name: str, off: int, devid: int, flags: int = 0) -> bytes:
    rec = bytearray(48)
    rec[0] = flags
    rec[16:19] = off.to_bytes(3, "little")
    struct.pack_into("<H", rec, 26, devid)
    nb = name.encode()
    rec[32:32 + len(nb)] = nb
    return bytes(rec)


def run(blob: bytes) -> str:
    d = Path(tempfile.mkdtemp())
    try:
        (d / "tpl.dtsi").write_text(TEMPLATE)
        tpl = J.parse_template(str(d / "tpl.dtsi"))
        return J.emit(tpl, P.parse(blob), "tpl.dtsi", "deadbeef")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def test_no_duplicate_addresses() -> None:
    print("[emit] 重复偏移不得生成重复节点")
    blob = synth("AIC", 0x110, 15) + synth("ECPU_0", 0, 1) + synth("GPX", 0, 512)
    out = run(blob)
    addrs = re.findall(r"power-controller@([0-9a-f]+)\s*\{", out)
    check(addrs == sorted(set(addrs), key=lambda x: int(x, 16)) or len(addrs) == len(set(addrs)),
          "节点地址无重复:%s" % addrs)
    check(len(addrs) == 1, "只有 1 个唯一地址的节点被写出")
    check("0x00000" in out or "GPX" in out, "重复偏移的条目进了末尾注释块")


def test_matched_keeps_structure() -> None:
    print("[emit] 匹配上的条目要抄 M4 的结构")
    out = run(synth("AIC", 0x118, 15))
    check('compatible = "apple,t8142-pmgr-pwrstate", "apple,t8103-pmgr-pwrstate"' in out,
          "compatible 换成 t8142")
    check("power-controller@118" in out, "地址用 M5 的 0x118(不是 M4 的 0x110)")
    check("apple,always-on" in out, "always-on 从 M4 模板带过来")
    check('label = "aic"' in out, "label 用 M4 模板的(小写)")


def test_unmatched_is_marked() -> None:
    print("[emit] 模板里没有的要标注不确定")
    out = run(synth("BRANDNEW", 0x900, 999))
    check("M4 模板里没有同名项" in out, "有警告注释")
    check('label = "brandnew"' in out, "label 小写")


def test_parse_template() -> None:
    print("[template] 解析")
    d = Path(tempfile.mkdtemp())
    try:
        (d / "t.dtsi").write_text(TEMPLATE)
        t = J.parse_template(str(d / "t.dtsi"))
        check("aic" in t, "按小写 label 索引")
        check(t["aic"]["offset"] == 0x110, "偏移解析")
        check(t["aic"]["always_on"] is True, "always-on 识别")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    for fn in (test_parse_template, test_no_duplicate_addresses,
               test_matched_keeps_structure, test_unmatched_is_marked):
        fn()
        print()
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
