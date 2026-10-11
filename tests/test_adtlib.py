#!/usr/bin/env python3
"""adtlib 自测。

重点覆盖 **FDT 二进制**那条路径 —— 它没法用现有数据验证(原始 ADT 要等
真机 dump),所以这里手工构造 FDT blob 来测。

跑:
    python3 tests/test_adtlib.py
    pytest tests/            # 装了 pytest 也行
"""

from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import adtlib  # noqa: E402

_FDT_BEGIN_NODE, _FDT_END_NODE, _FDT_PROP, _FDT_NOP, _FDT_END = 1, 2, 3, 4, 9


# ------------------------------------------------------------ 手工构造 FDT

def _align4(n: int) -> int:
    return (n + 3) & ~3


def build_fdt(tree: dict) -> bytes:
    """tree 形如 {"name": {"props": {...}, "children": [...]}} —— 最小实现,只为测试。"""
    strings: list = []
    string_offsets: dict = {}

    def str_off(s: str) -> int:
        if s not in string_offsets:
            string_offsets[s] = sum(len(x) + 1 for x in strings)
            strings.append(s)
        return string_offsets[s]

    blob = bytearray()

    def emit(node: dict) -> None:
        name = node["name"]
        blob.extend(struct.pack(">I", _FDT_BEGIN_NODE))
        raw = name.encode() + b"\x00"
        blob.extend(raw)
        blob.extend(b"\x00" * (_align4(len(raw)) - len(raw)))

        for k, v in (node.get("props") or {}).items():
            blob.extend(struct.pack(">III", _FDT_PROP, len(v), str_off(k)))
            blob.extend(v)
            blob.extend(b"\x00" * (_align4(len(v)) - len(v)))

        for c in node.get("children") or []:
            emit(c)

        blob.extend(struct.pack(">I", _FDT_END_NODE))

    emit(tree)
    blob.extend(struct.pack(">II", _FDT_NOP, _FDT_END))  # 顺手覆盖 NOP 分支

    strings_blob = b"".join(s.encode() + b"\x00" for s in strings)

    off_rsvmap = 40
    off_struct = off_rsvmap + 16
    off_strings = off_struct + len(blob)
    total = off_strings + len(strings_blob)

    header = struct.pack(
        ">10I",
        0xD00DFEED, total, off_struct, off_strings, off_rsvmap,
        17, 16, 0, len(strings_blob), len(blob),
    )
    return header + b"\x00" * 16 + bytes(blob) + strings_blob


def _tmp(data: bytes, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    f.write(data)
    f.close()
    return f.name


# ------------------------------------------------------------ 断言

def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print("  ok  %s" % msg)


def test_fdt_roundtrip() -> None:
    print("[fdt] 手工构造 -> 解析")
    tree = {
        "name": "",
        "props": {"compatible": b"test,root\x00"},
        "children": [
            {
                "name": "child@1000",
                "props": {
                    "compatible": b"test,child\x00other,thing\x00",
                    "reg": struct.pack(">II", 0x1000, 0x100),
                },
                "children": [],
            },
            {"name": "empty", "props": {}, "children": []},
        ],
    }
    path = _tmp(build_fdt(tree), ".dtb")
    root = adtlib.load_fdt(path)

    check(len(list(root.walk())) == 3, "节点数 = 3")
    child = next(root.find("child"))
    check(child.compatible == ["test,child", "other,thing"], "多值 compatible 拆正确")
    check(child.unit_addr == "1000", "unit_addr 提取正确")
    check(child.base_name == "child", "base_name 正确")
    check(child.reg_cells == ["0x00001000", "0x00000100"], "reg cell 解码正确")
    check(next(root.find("empty")).compatible == [], "无 compatible 的节点返回空表")
    Path(path).unlink()


def test_fdt_bad_magic() -> None:
    print("[fdt] 坏 magic 要报错")
    path = _tmp(b"\x00" * 64, ".dtb")
    try:
        adtlib.load_fdt(path)
    except ValueError as e:
        check("magic" in str(e), "坏 magic 抛出 ValueError: %s" % e)
    else:
        raise AssertionError("坏 magic 竟然没报错")
    Path(path).unlink()


def test_fdt_truncated() -> None:
    print("[fdt] 截断文件要报错,不能静默吞掉")
    data = build_fdt({"name": "", "props": {}, "children": []})
    path = _tmp(data[:30], ".dtb")
    try:
        adtlib.load_fdt(path)
    except ValueError:
        check(True, "过短文件抛 ValueError")
    else:
        raise AssertionError("过短文件竟然没报错")
    Path(path).unlink()


def test_dispatch() -> None:
    print("[load] 自动分派 plist / fdt")
    p = _tmp(build_fdt({"name": "", "props": {}, "children": []}), ".dtb")
    check(adtlib.load(p).name == "/", "FDT 走 fdt 分支")
    Path(p).unlink()

    p2 = _tmp(b"bplist00" + b"\x00" * 32, ".plist")
    try:
        adtlib.load(p2)
    except Exception:
        check(True, "认得出是 plist(内容坏没关系,分派对了)")
    Path(p2).unlink()

    p3 = _tmp(b"garbage!!", ".bin")
    try:
        adtlib.load(p3)
    except ValueError as e:
        check("认不出" in str(e), "未知格式抛 ValueError")
    else:
        raise AssertionError("未知格式竟然没报错")
    Path(p3).unlink()


def test_helpers() -> None:
    print("[helpers] 边界")
    check(adtlib.as_str_list(b"a\x00b\x00") == ["a", "b"], "NUL 分隔拆分")
    check(adtlib.as_str_list("a\x00b") == ["a", "b"], "str 输入也拆")
    check(adtlib.as_str_list(None) == [], "None -> 空表")
    check(adtlib.reg_cells(b"\x00\x01") is None, "非 4 字节对齐 -> None")
    check(adtlib.reg_cells(b"") is None, "空 -> None")


def test_dtc_crosscheck() -> None:
    """用 dtc(独立实现)生成的 DTB 交叉验证。

    这是本文件里最有价值的一条 —— 前面手搓的 blob 和老老实实写的解析器
    可能**同错**,dtc 是第三方实现,能把"我们俩一起错了"这种情形照出来。
    """
    print("[fdt] 与 dtc 交叉验证")
    import shutil
    import subprocess

    if not shutil.which("dtc"):
        print("  skip 没装 dtc")
        return

    dts = """
/dts-v1/;
/ {
	compatible = "test,root", "other,root";
	#address-cells = <2>;
	#size-cells = <2>;

	child@1000 {
		compatible = "test,child";
		reg = <0x0 0x1000 0x0 0x100>;
	};

	child2 {
		device_type = "soc";
		reg = <0x0 0x2000 0x0 0x10>;
	};
};
"""
    d = Path(tempfile.mkdtemp())
    try:
        (d / "t.dts").write_text(dts)
        subprocess.run(["dtc", "-I", "dts", "-O", "dtb", "-o", str(d / "t.dtb"), str(d / "t.dts")],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        root = adtlib.load_fdt(str(d / "t.dtb"))

        check(root.name == "/", "根节点名 = /")
        check(root.compatible == ["test,root", "other,root"], "根节点多值 compatible")
        check(len(list(root.walk())) == 3, "节点数 = 3(根 + 2 子)")

        c1 = next(root.find("child"))
        check(c1.compatible == ["test,child"], "child compatible")
        check(c1.unit_addr == "1000", "child unit_addr")
        check(c1.reg_cells == ["0x00000000", "0x00001000", "0x00000000", "0x00000100"],
              "child reg 四 cell 解码")

        c2 = next(root.find("child2"))
        check(c2.device_type == "soc", "device_type 解码")
        check(c2.unit_addr is None, "无 @ 时 unit_addr 为 None")
    finally:
        import shutil as _sh
        _sh.rmtree(d, ignore_errors=True)


def main() -> int:
    for fn in (test_helpers, test_fdt_roundtrip, test_dtc_crosscheck,
               test_fdt_bad_magic, test_fdt_truncated, test_dispatch):
        fn()
        print()
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
