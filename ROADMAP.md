# 工作清单

> 每一步的**具体命令、判据、排错**见 [docs/PLAYBOOK.md](docs/PLAYBOOK.md) 与
> [docs/M1-RUNBOOK.md](docs/M1-RUNBOOK.md)。本文件只管"要做什么"。

`[ ]` 待做 · `[x]` 完成 · `[!]` 阻塞中

---

## ⚠️ 2026-10-11 大改:别人已经做过的,不再做

调查发现 `ImAtomiskk/asahim5` 在**同一台机器(J704)**上已经走过 M1,
进度到"**启动 Linux 约 80-90%**"。他的笔记(方法、命令、踩坑)全部可用。

**所以本清单从"我们要做什么"改成"别人做到哪了、我们从哪接"。**

---

## 别人已经做完的(直接用,别重做)

| 阶段 | 状态 |
|---|---|
| 编译 m1n1 | ✅ macOS 和 Ubuntu 两条路都跑通 |
| 装 m1n1 到 J704 | ✅ `kmutil configure-boot` 的**完整实测命令** |
| m1n1 proxy 模式 | ✅ `/dev/ttyACM0` 能连 |
| m1n1 hypervisor 模式 | ✅ "基本能用" |
| **dump 原始 ADT** | ✅ `dump/m5_adt.bin` / `.txt` **已公开** |
| 编译 asahi Linux 源码 | ✅ 2026-10-03 |
| 引导 U-Boot | ❌ 没做 |
| 写驱动 | ❌ 没做 |
| **真正启动 Linux** | ❌ **"约 80-90%"** |

**我们的路线:复现到他的位置,然后从他卡住的地方往下走。**

---

## 阶段 0 · 硬件准备

- [x] M5 备份已验证可恢复
- [x] DFU 兜底就位
- [x] 数据线已验证
- [ ] 游戏本装 **Ubuntu Desktop** 双系统
- [ ] ⭐ **先下好一个 macOS IPSW 存着**(ipsw.me)—— DFU 恢复要用,
      没它走到"圆圈叹号"就全完了
- [ ] M5 上**关掉 FileVault** ← 原来漏了

---

## 阶段 1 · 复现 M1(全部是别人验证过的步骤)

见 [M1-RUNBOOK](docs/M1-RUNBOOK.md)。

- [ ] 编译 m1n1(要 `.macho` + `.bin` 两个产物)
- [ ] 进 1TR(判据:工具菜单里有「恢复助理」)
- [ ] `kmutil configure-boot -v "/Volumes/Macintosh HD - Data"`
- [ ] `python3 proxyclient/tools/shell.py` 连上
- [ ] `p.chip_id()` 返回 T8142

**判据**:拿到 proxy shell。**读出来全是 0 是已知问题,不算失败。**

---

## 阶段 2 · ⭐ 从这里开始是**没人做成的地方**

### 2a 抓 m1n1 启动日志(第一件事)

```bash
picocom -b 115200 /dev/ttyACM0 | tee m5_boot_log.txt
```

m1n1 启动时会打印**真实地址表**。**这是所有后续工作的地基。**

- [ ] 拿到完整启动日志
- [ ] 存进仓库(脱敏后)

### 2b 修 proxy client 的 MMIO 基址

> **别人的卡点**:`proxyclient/hw/` 里硬编码的是 M1/M2 时代的地址,
> 所以 `p.read32` 全返回 0。

- [ ] 把启动日志里的地址与 `proxyclient/hw/` 对比
- [ ] 锚定 UART(它本来就活着),让 `read32` 返回非零
- [ ] 判断偏移是否**统一** —— 统一则改一处就够

**判据**:`p.read32(<UART基址>)` 返回非零。

### 2c 原始 ADT

- [x] **已经拿到了**(ImAtomiskk 公开的 `m5_adt.txt`)
- [ ] 用 m1n1 自带的 `proxyclient/adt.py` 自己 dump 一份对账
- [ ] 记录来源

---

## 阶段 3 · 设备树

- [x] 地址翻译规则已解并核实(**+`0x2_1000_0000`**,11/11 全中)
- [ ] **用 m1n1 自带的 `proxyclient/tools/pmgr_adt2dt.py`** 生成 —— 别再自己写
- [ ] 我们的 `dts/t8142.dtsi` / `t8142-pmgr.dtsi` 保留作对照,不重写
- [ ] 对照两份现成设备树(rhelvista 的**地址有错**,sentaxic 的是 pre-boot)

---

## 阶段 4 · ⭐ **真正的墙:内核启动**

> 别人卡在这,进度"约 80-90%"。

已知的障碍:

- **WFI chicken bit**(M4 起):核一进 idle 就挂。Asahi 的 workaround 是内核命令行
  关掉 WFI idle,补丁在 linux-next
- **副核启动 / SMP**
- **PSCI 缺失**:Apple CPU 没有 EL3,Asahi 在推 m1n1 提供的 UEFI Runtime Services 版 PSCI

- [ ] 编译 linux-asahi,带上 WFI workaround
- [ ] tethered 引导内核(`proxyclient/tools/linux.py`)
- [ ] **串口出字** ← 第一个真实里程碑

---

## 阶段 5 · 外设(别人的路线图:第 2 年)

策略:**从 M3 base(T8122)拿现成驱动,加 T8142 compatible。**

- [ ] 简单驱动:UART / I2C / GPIO / SMC / SPMI / DART / PCIe / NVMe
      —— 大多是"加一行 compatible"
- [ ] 视频解码(linux-asahi 有 M3 base 版,应该好移)
- [ ] 显示(DCP)—— 难,WIP
- [ ] USB / DP Alt Mode —— WIP
- [ ] Wi-Fi(BCM4387,移植 Asahi 的 brcmfmac 补丁)
- [ ] GPU(AGX)—— **最长的一根杆**,不要计划

---

## 待定问题

1. **核 compatible 叫什么?** `sawtooth`/`everest`(ADT)vs `Hidra`(MIDR)。
   两份第三方文档也都标了这个问题,**都没解决**。真机读 MIDR 才能定。
2. **proxy client 的偏移是不是统一的?** 决定修基址是"改一处"还是"逐个来"。

---

## 里程碑速览

```
M0  Ubuntu + IPSW + 关 FileVault        ← 现在
M1  复现 m1n1 proxy(别人已通)          ← 照手册走
M2  抓启动日志 + 修 proxy 基址           ← ⭐ 从这开始是新东西
M3  原始 ADT(已有)                     ← 对账
M4  设备树(用 m1n1 自带工具)
M5  内核启动 + WFI workaround           ← ⭐ 真正的墙
M6  串口出字
M7+ 外设(年计)
```
