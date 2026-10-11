# ⚠️ ioreg 视图的三条陷阱

深度审计(2026-10-11 第二轮)发现:我们的工具**大多建立在 ioreg 视图上**,
而那份数据有三个和原始 ADT 不同的地方。

**结论:ioreg 能用,但要知道它多给了什么、少给了什么。**

---

## 1 ioreg 会**合成**节点

ioreg 里有一批**原始 ADT 里不存在**的节点,是 XNU/IOKit 造出来的:

```
AppleANS3CGv2Controller        AppleTypeCRetimer ×3
displaymanager                 Root
ExclaveOSIntegrityCatalog      ExclaveOSTrustCache
handoff                        hibernation
exclave-memory-map             exclave-misc
bluetooth-pcie                 ...
```

**后果**:任何按节点数统计、或按节点生成输出的工具,都会**多算**这些。
(我们的 `adt_report.py` / `adt2dts.py` 就有这个问题。)

---

## 2 ioreg 会**展开**节点

原始 ADT 里:

```
mapper-acio0          ← 一个节点,无子节点
  compatible = [iommu-mapper]
  device_type = dart-mapper
```

ioreg 里同一个东西变成 **24 个子节点**:

```
mapper-acio0-rx-0 ... mapper-acio0-rx-11
mapper-acio0-tx-0 ... mapper-acio0-tx-11
```

**后果**:`mapper-*` 相关的节点数从 3(原始)膨胀到 137(ioreg)。

---

## 3 两份数据来自**不同固件**

| | 固件 | 来源 |
|---|---|---|
| 我们的 ioreg | macOS **27.0.1**(26A434) | 本机 |
| `m5_adt.txt` | `EmbeddedDeviceTrees-**11156.1.2**`,2025-08-15 | `ImAtomiskk/asahim5` |

**实测差异:**

| 项 | 我们的 ioreg | 他的 ADT |
|---|---|---|
| 节点总数 | 527 | **432** |
| compatible 集合 | 136 | **134**(交集 132) |
| PMGR 设备数 | 387 | **386**(差 `DISP-SYS-V`) |

**只有 ioreg 有的 compatible**:`dispmgr` `pci17a0,9755` `pciclass,080501` `pcie-sdreader`
**只有原始 ADT 有的**:`fpwm,t8101` `sgx`

> ⚠️ **所以"我们的数据"和"他的数据"混着用时要记得这件事。**
> **好消息**:SoC 级的东西(地址、DART、ps-groups)两边**完全一致** —— 见下。

---

## ✅ 反过来:这些经查是**一致的**

| 项 | 我们的 ioreg | 他的 ADT |
|---|---|---|
| `ps-groups` 三组内容 | `0/0/0`, `1/0/0`, `48/0/0` | **逐字一致** |
| `dart,t8110` 数量 | 33 | **33** |
| 关键外设地址(pmgr/aic/wdt/pinctrl/i2c/uart) | — | **11/11 全中** |

**所以:ioreg 拿来做"地址和设备识别"是可靠的;
用来做"节点清单/节点数"要当心。**

---

## 用法建议

| 想干什么 | 用哪份 |
|---|---|
| 地址、compatible(块级) | 两份都行,已交叉验证 |
| **节点清单 / 节点数 / 生成设备树** | **用原始 ADT**(`tools/adt_txt.py`) |
| 和 M4 对照 | 注意固件版本差异 |

> 我们唯一直接读原始 ADT 的工具是 **`adt_txt.py`**。
> 其余工具都读 ioreg —— **知道这个前提再用。**
