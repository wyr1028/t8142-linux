# 进度总览

一页看完:这项目是什么、到哪了、卡在哪、下一步。
**(接手入口。2026-10-11 全面重写 —— 旧版说的和现实不符了。)**

---

## 一句话

让 **Linux 原生跑在 Apple M5**(本机 MacBook Pro 14",`Mac17,2` / 板号 J704 / SoC `t8142`)上。
**独立项目:能用任何上游的东西,但不回馈、不合并。**

---

## ⚠️ 先知道这条:官方**没有**在做 M5

官方特性支持页(`AsahiLinux/docs` 的 `platform/feature-support/m5.md`):
**M5 全部 `TBA`** —— 官方定义是 *"Active work on this feature is **not being undertaken
at this time**"*(比 WIP 还低一档)。Installer = **no**。

**在做的全是社区。** 所以我们没有官方时间表可等。

---

## 现在到哪了

```
纸面工作      ✅ 做完了(而且被别人验证过)
真机工作      ❌ 一步没动 —— 卡在"游戏本还没装 Linux"
```

**四个好消息:**

1. **有人在同一台机器(J704)上把 M1 走通了** —— `ImAtomiskk/asahim5`,
   进度到"**启动 Linux 约 80-90%**",完整流程和踩坑都公开了
2. **⭐ 原始 ADT 已经从本机 macOS 里提取出来** —— **不用 m1n1、不用等硬件**
   (`tools/extract_adt.py`,571 节点,地址 11/11 全中)
3. **地址规则已解且交叉验证** —— 121 条对账一致
4. **官方文档全套拿到** —— 流程、端口、依赖、kernel config 位置都有

---

## 已核实的关键事实

| 事实 | 值 | 怎么核的 |
|---|---|---|
| SoC | **T8142 / H17G / Hidra** | 官方代号表 |
| 目标机器 | Mac17,2 / **J704AP** | 官方设备表 |
| 地址翻译 | **物理 = ADT 子地址 + `0x2_1000_0000`** | 原始 ADT 的 `arm-io/ranges`(一手)+ 121 条交叉验证 |
| PMGR 差异 | 名字重合 **92%**,偏移重合 **6%** | 用原始 ADT 重验,数字不变 |
| AIC | **v3(`aic,3`)**,M3/M4 同款 | m1n1 有 aic3 代码;Linux 认 `apple,t8122-aic3`;**定时器绕过 AIC** |
| m1n1 支持 | ✅ 上游原样支持 T8142(PR #629/#578) | ImAtomiskk 用未改的上游 submodule 就跑通了 |

---

## ⭐ 两个**没人做成**的事 —— 我们在的地方

| | 状态 |
|---|---|
| **修 proxy client 的 MMIO 基址** | ❌ `proxyclient/hw/` 里硬编码 M1/M2 地址 → `read32` 全返回 0。没人修好 |
| **内核启动过 WFI** | ❌ 别人"约 80-90%"。WFI chicken bit + SMP + PSCI 缺失 |

**其余的坑都有人趟过了。**

---

## 卡在哪

**游戏本还没装 Linux。** 这是唯一的动作项。

准备清单:

| 项 | 状态 |
|---|---|
| M5 备份已验证可恢复 | ✅ |
| DFU 兜底(M3 MBA + Apple Configurator) | ✅ |
| 数据线已验证 | ✅ |
| **先下好一个 macOS IPSW 存着** | ⬜ ⚠️ **唯一事后补不了的** |
| M5 关掉 FileVault | ⬜ |
| 游戏本装 Ubuntu Desktop | ⬜ |

---

## 已有产物

**工具**(`tools/`,`make test` 全绿)

| 工具 | 干什么 |
|---|---|
| `adtlib.py` | ADT 读取层(ioreg plist + 标准 FDT) |
| **`adt_txt.py`** | **解析原始 ADT 的文本 dump**(Apple 私有格式读不了文本可以)。`--ranges` / `--memmap` / `--list` / `--tree` |
| `adt2dts.py` | ADT → DTS 骨架 / 列 compatible / 找节点 |
| `compat_diff.py` | compatible 差集 |
| `adt_report.py` | 硬件清单 |
| `pmgr_devices.py` | PMGR `devices` 解码(386/387 条) |
| `pmgr_join.py` | M4 结构 + M5 数值 → pmgr dtsi |
| `scrub_adt.py` | 洗敏感字段 + 发布前自查 |
| **`check_host.sh`** | **在 Linux 主机上跑的自检** |
| **`extract_adt.py`** | **从本机 macOS 提取 ADT**(Preboot 卷的 im4p → DER → LZFSE)** |

**文档**(`docs/`,13 份)。按"现在最该看"排序:

| 文件 | 内容 |
|---|---|
| **`M1-RUNBOOK.md`** | **M1 逐条手册**(官方流程 + 第三方实测) |
| **`M5-PRIOR-ART.md`** | 别人做了什么、没做什么、能用的都用上 |
| `OFFICIAL-TETHERED-BOOT.md` | 官方 tethered boot 文档要点 |
| `PLAYBOOK.md` | M0→M7 操作手册 |
| `M5-MEMMAP.md` | M5/J704 内存映射(原始 ADT 生成,已交叉验证) |
| `ROADMAP.md` | 工作清单 |
| `PROVENANCE.md` | **每个事实的来源** —— 接手前必读 |
| `HARDWARE.md` / `PMGR-DEVICES.md` / `PMGR-DELTA.md` / `DTS-BACKLOG.md` | 技术细节 |
| `RISKS.md` / `DEPENDENCIES.md` | 风险与许可 |

---

## 三条必须守住的

1. **不碰任何 Apple 未公开资料**(唯一红线)
2. **外发前过 `scrub_adt.py --verify`**
3. **不声称 clean room** —— 本项目声明使用 AI,见 [AI-USAGE](../AI-USAGE.md)

---

## 下一步

```
1. 下好 macOS IPSW 存着        ← 唯一补不了的
2. M5 关 FileVault
3. 游戏本装 Ubuntu Desktop
4. bash tools/check_host.sh    ← 全绿才继续
5. 照 M1-RUNBOOK 走
```
