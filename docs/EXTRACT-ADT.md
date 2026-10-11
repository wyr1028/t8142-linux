# ⭐ 从本机 macOS 提取 ADT —— **不用 m1n1**

**2026-10-11 发现并跑通。这让 M2 从"要等 tethered boot"变成"已经做完"。**

---

## 结论

macOS 的 Preboot 卷里存着固件发布时的设备树:

```
/System/Volumes/Preboot/<UUID>/restore/Firmware/all_flash/DeviceTree.j704ap.im4p
```

**一个命令就能解出原始 ADT:**

```bash
python3 tools/extract_adt.py -o raw-adt.bin
cd m1n1/proxyclient && python3 -m m1n1.adt raw-adt.bin > adt.txt
```

参考:`AsahiLinux/docs` 的 `docs/fw/adt.md`「Option 2」。

---

## 实测结果(J704)

| 项 | 值 |
|---|---|
| im4p | `DeviceTree.j704ap.im4p`,63,307 字节 |
| 格式 | ASN.1 DER:`SEQUENCE { "IM4P", "dtre", "EmbeddedDeviceTrees-12661.1.5", OCTET STRING }` |
| payload | 63,246 字节,**LZFSE 压缩**(magic `bvx2`),**未加密** |
| 解压后 | **460,748 字节** |
| ADT 魔数 | `0x17`(小端) |
| 解码后 | **24,668 行 / 571 个节点** |

---

## ⭐ 三份数据一对比,之前的疑点解开了

| 来源 | 固件 | 节点数 |
|---|---|---|
| **我们的 ADT**(本机提取) | `EmbeddedDeviceTrees-12661.1.5`(2026-08) | **571** |
| 我们的 ioreg | macOS 27.0.1 | 527 |
| ImAtomiskk 的 ADT | `EmbeddedDeviceTrees-11156.1.2`(2025-08) | 432 |

**原始 ADT 确实比 ioreg 多(571 > 527)** —— 印证了"ioreg 被过滤"。

之前看到"432 < 527"一头雾水,**那是固件差了一整年**,不是解析问题。

---

## ✅ 地址:11/11 全中

用**我们自己的 ADT** 再核一遍:

```
pmgr / aic / wdt / nub-gpio / smc-gpio / aop-gpio / gpio0
i2c0 / i2c4 / fpwm0 / uart0
        ↓
11 个全部 ✅ 与"ioreg + 0x2_1000_0000"一致
```

翻译窗口也从我们自己的 ADT 里读到:`bus 0x0 → phys 0x2_1000_0000, size 0x3_F000_0000` ✓

---

## 🔒 安全性:解出来的文本**可以直接公开**

m1n1 的 `adt.py` 把敏感值渲染成**引用符号**,不是真值:

```
serial-number     = << syscfg/SrNm/0x20,zeroes/0x20 >>
mlb-serial-number = << syscfg/MLB#/0x20,zeroes/0x20 >>
local-mac-address = << macaddr/wifiaddr,syscfg/WMac/6,zeroes/6 >>
uid-aes-key       = 0
boot-nonce        = 0
```

实测核对:
- **本机序列号出现次数:0**
- **真 UUID 模式:0**
- **真 MAC 模式:0**

长十六进制串全是硬件功能数据(`perf-counters`、`agx-af-wr-bw-threshold`、`temp-sensor`…)。

---

## ⚠️ 限制:iBoot 启动时才填的值,这份里是 **0**

官方文档(`docs/fw/adt.md`)写着:

> "(these are) **missing details filled in by iBoot during boot**"

**实测确认了。** 拿我们的和 ImAtomiskk 的**真机 m1n1 dump** 逐项比:

### ❌ 我们缺的(boot 时由 iBoot 填,im4p 里是占位 0)

| 属性 | 我们(im4p) | 他(m1n1 真机) |
|---|---|---|
| `chip-id` | `0` | 真值 |
| `board-id` | `0` | 真值 |
| `chip-revision` | `0` | `32` |
| **`clock-frequencies`** | **`[0, 0, 0, …]`** | **真实频率表** |
| `boot-*` / `manifest-*` / `nonce` | `0` | 真值 |

零值属性总占比:我们 12%,他 11% —— **数量相近**,但**具体缺哪几个**在下面。

### ✅ 设备树真正要用的,**全都在**

| 属性 | 状态 |
|---|---|
| `reg`(地址) | ✅ **11/11 核对通过** |
| `interrupts` | ✅ **156 个节点与真机 dump 完全相同,0 个不同** |
| `compatible` / `device_type` | ✅ |
| `ranges`(翻译窗口) | ✅ |
| `clock-ids` | ✅(35 处全非零) |
| PMGR `devices` | ✅ 387 条(比他多 1 —— 我们固件新一年,多的那条是 `DISP-SYS-V`) |

### 结论

| 用途 | 这份够不够 |
|---|---|
| **写设备树(节点/地址/中断/电源域)** | ✅ **够** |
| **时钟频率**(调频驱动) | ❌ **缺** —— 但那在很后面,且真机可从寄存器读 |
| `chip-id` / `board-id` / `chip-revision` | ❌ 缺 —— 但 m1n1 本来就从寄存器读,不依赖 ADT |

**所以:结构完全可用,少数"boot 时填写"的数值缺失。**
要 100% 完整的,仍然要 m1n1 从真机 dump —— 那仍然是 M1 要干的事。

---

## 同目录下还有

同一个 `restore/Firmware/` 里还有本机的一整套固件:

```
sptm.t8142.release.im4p      txm.macosx.release.im4p
t8142dcp.im4p                t8142pmp.im4p
t8142.msrf.im4p              aop2fw-j704aop2.RELEASE.im4p
J704_MtpFirmware.im4p        J704_Multitouch.im4p
J704_InputDevice.im4p        SmartIOFirmware_ASCv7.im4p
```

> ⚠️ **这些先别碰。** 读设备树是"功能性数据";
> **反编译 SPTM/TXM 那种二进制代码是另一回事** —— 见 [LEGAL.md](../LEGAL.md)。
> 要动得先明确决定,别顺手就上。
