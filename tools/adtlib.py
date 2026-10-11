#!/usr/bin/env python3
"""ADT(Apple Device Tree)读取层。

两种输入:
  ioreg plist —— macOS 的 IODeviceTree 平面视图(经 XNU 过滤,开发期可用)
  FDT 二进制  —— 原始 ADT blob,标准 FDT 结构

Apple 的 ADT 是 FDT 的变体:结构块遵循标准 FDT,但部分属性(尤其 reg 与
中断相关)的语义是 Apple 私有的。本模块只保证**结构**解析正确,语义解读
由调用方负责 —— 见 docs/PROVENANCE.md 的来源纪律。
"""

from __future__ import annotations

import plistlib
import struct
from dataclasses import dataclass, field
from typing import Iterator, Optional

# --------------------------------------------------------------- 节点模型


@dataclass
class Node:
    name: str
    props: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    @property
    def base_name(self) -> str:
        """去掉单元地址后的节点名。"""
        return self.name.split("@", 1)[0]

    @property
    def unit_addr(self) -> Optional[str]:
        """节点名里 '@' 之后的部分。"""
        return self.name.split("@", 1)[1] if "@" in self.name else None

    @property
    def compatible(self) -> list:
        return as_str_list(self.props.get("compatible"))

    @property
    def device_type(self) -> Optional[str]:
        v = as_str_list(self.props.get("device_type"))
        return v[0] if v else None

    @property
    def reg_cells(self) -> Optional[list]:
        return reg_cells(self.props.get("reg"))

    def walk(self, depth: int = 0) -> Iterator[tuple]:
        yield self, depth
        for c in self.children:
            yield from c.walk(depth + 1)

    def find(self, base_name: str) -> Iterator["Node"]:
        for n, _ in self.walk():
            if n.base_name == base_name:
                yield n


# --------------------------------------------------------------- 值解码


def as_str_list(v) -> list:
    """ADT 字符串属性是 NUL 分隔的一串,也可能已是 str。"""
    if v is None:
        return []
    if isinstance(v, (bytes, bytearray)):
        return [s for s in v.decode("utf-8", "replace").split("\x00") if s]
    if isinstance(v, str):
        return [s for s in v.split("\x00") if s]
    return [str(v)]


def reg_cells(v) -> Optional[list]:
    """大端 u32 序列 -> ['0x........', ...]。非 4 字节对齐返回 None。

    注意:这里**不做** #address-cells / #size-cells 的解释 —— Apple 的 reg
    编码与设备树的那个约定不完全一致,硬解释会得出错误的地址。
    只把原始 cell 摆出来,由人判断。
    """
    if not isinstance(v, (bytes, bytearray)) or len(v) == 0 or len(v) % 4:
        return None
    return ["0x%08x" % struct.unpack_from(">I", v, i)[0] for i in range(0, len(v), 4)]


# --------------------------------------------------------------- ioreg 输入

# ioreg 的 IODeviceTree 平面里混着 IOKit 自身的键,不是 ADT 属性,解析时丢弃。
_IOKIT_EXACT = frozenset({
    "IOConsoleLocked", "IOConsoleUsers", "IOKitBuildVersion", "IOKitDiagnostics",
    "OS Build Version", "OSKernelCPUSubtype", "OSKernelCPUType", "OSPrelinkKextCount",
    "IOObjectClass", "IOObjectRetainCount", "IORegistryEntryID",
    "IORegistryEntryName", "IORegistryEntryChildren", "IORegistryEntryLocation",
    "IORegistryPlanes", "IOReportLegend", "IOReportLegendPublic",
    "IOServiceBusyState", "IOServiceBusyTime", "IOServiceState",
    "IODeviceMemory", "IOInterruptControllers", "IOInterruptSpecifiers",
})
# "IO"/"OS" 前缀(大小写敏感):ADT 自己的属性不会这样开头
_IOKIT_PREFIX = ("IO", "OS")


def _is_iokit_key(k: str) -> bool:
    return k in _IOKIT_EXACT or k.startswith(_IOKIT_PREFIX)


def load_ioreg(path: str) -> Node:
    with open(path, "rb") as f:
        root = plistlib.load(f)
    if not isinstance(root, dict):
        raise ValueError("顶层不是 dict,不像是 ioreg plist")
    return _from_ioreg(root)


def _from_ioreg(d: dict) -> Node:
    props = {k: v for k, v in d.items() if not _is_iokit_key(k)}
    kids = [_from_ioreg(c) for c in (d.get("IORegistryEntryChildren") or [])]
    return Node(name=d.get("IORegistryEntryName", "?"), props=props, children=kids)


# --------------------------------------------------------------- FDT 输入

_FDT_MAGIC = 0xD00DFEED
_FDT_BEGIN_NODE, _FDT_END_NODE, _FDT_PROP, _FDT_NOP, _FDT_END = 1, 2, 3, 4, 9


def load_fdt(path: str) -> Node:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 40:
        raise ValueError("文件太短,不是 FDT")
    (magic, _totalsize, off_struct, off_strings, _off_rsvmap,
     _ver, _lastver, _cpuid, size_strings, _size_struct) = struct.unpack_from(">10I", data, 0)
    if magic != _FDT_MAGIC:
        raise ValueError("magic 不匹配: 0x%08x(期望 0xd00dfeed)" % magic)
    if off_strings + size_strings > len(data):
        raise ValueError("字符串块越界")
    strings = data[off_strings:off_strings + size_strings]

    pos = off_struct
    stack: list = []
    root: Optional[Node] = None

    while pos < len(data):
        (tag,) = struct.unpack_from(">I", data, pos)
        pos += 4

        if tag == _FDT_BEGIN_NODE:
            end = data.index(b"\x00", pos)
            nm = data[pos:end].decode("utf-8", "replace")
            pos = (end + 1 + 3) & ~3
            node = Node(name=nm or "/")
            if stack:
                stack[-1].children.append(node)
            elif root is None:
                root = node
            stack.append(node)

        elif tag == _FDT_END_NODE:
            if not stack:
                raise ValueError("结构块 unbalanced(多余的 END_NODE)")
            stack.pop()

        elif tag == _FDT_PROP:
            length, nameoff = struct.unpack_from(">II", data, pos)
            pos += 8
            val = data[pos:pos + length]
            pos = (pos + length + 3) & ~3
            if nameoff >= len(strings):
                raise ValueError("属性名偏移越界")
            kend = strings.index(b"\x00", nameoff)
            key = strings[nameoff:kend].decode("utf-8", "replace")
            if stack:
                stack[-1].props[key] = val

        elif tag == _FDT_NOP:
            continue

        elif tag == _FDT_END:
            break

        else:
            raise ValueError("未知 tag %d @ 0x%x" % (tag, pos - 4))

    if root is None:
        raise ValueError("FDT 里没有节点")
    return root


# --------------------------------------------------------------- 自动分派


def load(path: str) -> Node:
    with open(path, "rb") as f:
        head = f.read(8)
    if head[:4] == b"bplist" or head[:1] == b"<" or head[:5] == b"<?xml":
        return load_ioreg(path)
    if head[:4] == b"\xd0\x0d\xfe\xed":
        return load_fdt(path)
    raise ValueError("认不出的输入(既不是 plist 也不是 FDT)")
