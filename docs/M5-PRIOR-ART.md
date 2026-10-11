# M5 上有没有人做过了 —— 调查结果

2026-10-11 广泛查了一遍。**结论:有先例,而且不止一个。**

---

## 1 现有工作一览

| 来源 | 内容 | 状态 |
|---|---|---|
| **m1n1 PR #629** | `Initial support for T8142` —— SoC id / UART base / MIDR / SMP offset / chickens | ✅ 已合并(2026-07-19) |
| **m1n1 PR #578** | pmgr 覆盖 M4 Pro/Max、A18 Pro、M5;修了 **M5 Max** 的 device-mode USB | ✅ 已合并 |
| **`AsahiLinux/linux` @ `76db823`** | **「M5 bringup + some hacks to get it booting」**(rhelvista,2026-07-18)—— 含 `t8142.dtsi` / `t8142-pmgr.dtsi` / `t8142-j813.dts` + 内核侧 hack | ⚠️ **不在 `asahi` 分支上**,未合并 |
| **`sentaxic/asahi-m5`** | M5 MacBook **Air**(`Mac17,3` / J813)的逆向。SoC 文档 + 地址表 + m1n1 补丁 + 最小设备树 | ⚠️ **pre-boot** —— 作者明说"没在真机上跑过,只验证了能编译" |
| WFI workaround | 修 M4/M5 上 WFI 导致寄存器归零的 chicken bit 问题 | ✅ **确认在 M5 上有效** |

### 1.0 🔴 **同一台机器(J704)上有人在跑 —— 而且昨天还在推**

**`ImAtomiskk/asahim5`**(2026-09-11 建,2026-10-10 最后推送)

| | |
|---|---|
| 机器 | **SoC: T8142 / Hidra (base M5, not Pro)** · **MoBo: j704** ← **和我们同一台** |
| 宿主 | Intel i7-11700KF + **Ubuntu Studio 26.04**(和我们选的路线一样) |
| 最新成果 | **(2026-10-03)为 M5 编译了 asahi Linux 源码** |
| **当前卡点** | **"M5 副核启动 / 内核启动"** |
| 已有 | m1n1 在他机器上**已经在跑**(`/dev/ttyACM0`)、u-boot、linux、**`dump/` 里有原始 ADT** |

**`dump/` 里有三份关键文件:**

| 文件 | 大小 | 内容 |
|---|---|---|
| `m5_adt.bin` | 573 KB | **原始 ADT 二进制**(Apple 私有格式,魔数 `0x17`,**不是标准 FDT**) |
| `m5_adt.txt` | 1.0 MB | **原始 ADT 的文本 dump**(已脱敏) |
| `m5_t8142.dts` | 33 KB | 他生成的设备树 |

**这意味着:我们说要靠 tethered boot 才能拿到的原始 ADT,现在就在手上了。**

> 该项目 README 写明 **"OPEN to contributions"**。但按[项目定位](../README.md),
> 我们**只取用、不回馈** —— 这一点要守住。

### 1.2 最值得看的两份

- **`sentaxic/asahi-m5` 的 `docs/T8142-SOC.md`** —— 信息密度最高,见下节
- **rhelvista 的 `t8142.dtsi`** —— **能启动**(commit 标题说的),可以当参考

---

## 2 从 `T8142-SOC.md` 挖到的关键信息

来源:MacBook Air M5(`Mac17,3` / J813),macOS 26.5.1,xnu-12377。

### 2.1 ⭐ 地址翻译规则(**解决了我之前搞错的那个**)

> arm-io `ranges` 把 SoC 内部子空间翻译到物理地址:**`+0x2_1000_0000`**
> (窗口 `0x3.F000_0000`)。M1/M2 用 `0x2_0000_0000`,**T8142 把整个 MMIO 窗口上移了**。

**所以从 ioreg 读出来的地址,加 `0x2_1000_0000` 就是设备树要的物理地址。**

实测:12 个节点里 **7 个精确命中**(pmgr / aic / wdt / pinctrl×3 / fpwm0)。

### 2.2 ⚠️→✅ AIC 是 **v3** —— 但**那不是问题**(我一度搞错了)

sentaxic 的文档说:

> M1 = AICv1,M2/M3/M4 = AICv2。T8142 报了 `aic,3` ——
> 一个 m1n1 和 Linux 都**不支持**的新版本。

**查源码后:这段话是错的。**

| 世代 | AIC | compatible |
|---|---|---|
| M1 | v1 | `apple,aic` |
| M2 | v2 | `apple,aic2` |
| **M3 / M4** | **v3** | **`apple,t8122-aic3`** |
| M5 | v3 | `aic,3` |

**M3 和 M4 用的就是 v3。** m1n1 有 `aic3` 结构体 + `aic23_init(3, node)`,
Linux 的 `irq-apple-aic` 也认 `apple,t8122-aic3`。

而且 m1n1 的 aic3 **从设备树动态读寄存器偏移** —— sentaxic 自己列出的那批
M5 属性(`cap0-offset` `aic-iack-offset` …)**正是它要的**。

> **教训**:这是同一类错误的第二次 —— 又一次把"看起来合理的第三方说法"
> 直接采信,没去查一手证据。**别人的文档也可能错。**

### 2.3 CPU 核名 —— 和我们的观察一致

> 4× P = `apple,everest`,6× E = `apple,sawtooth`
> ⚠️ 作者也标注了:**"匹配 A16 世代的命名,不是 M5 该有的。要拿 M4 的 ADT 对照"**

**和我们独立观察到的一致**(见 [HARDWARE.md §3](HARDWARE.md))。

### 2.4 其它

| 项 | 值 |
|---|---|
| SoC | T8142,chip-id `0x8142`,**单 die**,soc-generation **H17** |
| board-id | `0x24`,chip-revision `0x20` |
| UART0 | `uart-1,samsung` @ **`0x3_A520_0000`**,IRQ `0x4cf`(1231) |
| 物理访问 | **需要 Apple 的调试 USB-C 线** —— UART 通过 ACE3/SMC USB-PD 控制器复用到某个 USB-C 口 |

---

## 3 还没有人做的事

| | |
|---|---|
| M5 **base**(`Mac17,2` / J704 ——**我们的机器**)的启动报告 | ❌ 没找到 |
| J813 上真的启动成功 | ❌ 作者自述 pre-boot |
| M5 上的相机 / 显示 / GPU | ❌ 都没有 |
| Asahi 安装器支持 M5 | ❌ 官方不给 |

> 目前 M4/M5 的公认状态:**NVMe/PCIe 能识别、多核能启动、WFI workaround 有效**,
> 但**图形与外设全无**,所以安装器不提供。

---

## 4 对我们的意义

**好消息**

- 路径是通的 —— **M4 上已经有人跑到 shell**,M5 的 WFI 问题也有解
- 地址问题解决了(+`0x2_1000_0000`)
- 有现成的 `t8142.dtsi` 可参考(两份,一份还启动过)

**不确定的**

- 我们的机器(J704)**没人跑过**
- 那两份现成设备树**互相打架**(serial / i2c 的地址对不上),都需要真机验证
- 地址窗口**可能不止一个**(12 个节点里 5 个对不上 sentaxic 说的单一窗口)

**所以结论**:路径是通的,**没有已知的"必须从零写"的硬骨头**。
剩下的主要是真机验证 + 对账。

---

## 5 下一步(待真机)

1. 跑通 m1n1(M1)—— **大概率能跑通**,见下
2. 拿到**原始 ADT**(M2)—— 用来定地址窗口和确认 AIC 属性齐全
3. 核对两份现成设备树,定出 J704 的版本

---

## 6 m1n1 能起来吗?

**能,而且理由很硬:**

| 需要什么 | 状态 |
|---|---|
| 认出 T8142 | ✅ PR #629 已合并 |
| PMGR 初始化 | ✅ PR #578 覆盖 M5 |
| AIC v3 | ✅ **m1n1 早就有**(M3/M4 同款) |
| device-mode USB | ✅ 在 M5 Max 上修过 |
| UART | ✅ `EARLY_UART_BASE` 已定义 |

**而且 m1n1 跑在 Linux 之前** —— 它自己的需求很少:
UART、USB、PMGR、DART、AIC 屏蔽。**不需要 Linux 那套驱动栈。**

**最关键的一点**:我们现在要 m1n1 干的活是 **dump 原始 ADT(M2)**,
那件事**只需要 UART 或 USB** —— 连 AIC 都用不上。

> 所以即使 m1n1 在某些子模块上出问题,**只要串口/USB 通,我们就能拿到 ADT。**

---

## 附:引用来源

- `AsahiLinux/linux` commit `76db823`(rhelvista,2026-07-18)
- `sentaxic/asahi-m5`(README / `docs/T8142-SOC.md` / `docs/address-map.txt`)
- m1n1 PR #629 / #578
- Asahi Linux Linux 7.2 进度报告


---

## 7 ⭐ 用真实 ADT 的最终核实(2026-10-11)

拿到 `ImAtomiskk/asahim5` 的 `m5_adt.txt` 后,用我们的工具解析并核对。

### 7.1 翻译窗口 —— 从**一手数据**确认

`arm-io` 节点的 `ranges` 属性(原始 ADT 原文):

```
bus 0x0 → phys 0x2_1000_0000   size 0x3_F000_0000     Δ = 0x2_1000_0000
其余 21 个窗口 Δ = 0(恒等映射)
```

### 7.2 逐节点核对:**11/11 全中**

| 节点 | 原始 ADT 物理地址 | ioreg+Δ |
|---|---|---|
| `pmgr` | `0x380700000` | `0x380700000` ✅ |
| `aic` | `0x381000000` | `0x381000000` ✅ |
| `wdt` | `0x3882b0000` | `0x3882b0000` ✅ |
| `nub-gpio` | `0x3881f0000` | `0x3881f0000` ✅ |
| `smc-gpio` | `0x38c820000` | `0x38c820000` ✅ |
| `aop-gpio` | `0x390824000` | `0x390824000` ✅ |
| `gpio0` | `0x39a000000` | `0x39a000000` ✅ |
| `i2c0` / `i2c1` | `0x3a5010000` / `0x3a5014000` | 同 ✅ |
| `fpwm0` | `0x3a5040000` | `0x3a5040000` ✅ |
| `uart0` | `0x3a5200000` | `0x3a5200000` ✅ |

**结论:`物理地址 = ioreg 地址 + 0x2_1000_0000` 成立,而且是拿原始 ADT 验的。**

### 7.3 顺带发现:rhelvista 那份设备树**有错**

| 节点 | rhelvista 的 DTS | 真值(原始 ADT) |
|---|---|---|
| `serial0` | `0x385200000` | **`0x3_a5200000`** |
| `pinctrl_nub` | `0x388f0000` | **`0x3_881f0000`** |

> 所以**别直接抄那份"能启动"的文件** —— 它的注释说"some hacks to get it booting",
> 地址未必都对。**以原始 ADT 为准。**

### 7.4 工具

新增 `tools/adt_txt.py` —— 解析原始 ADT 的文本 dump(Apple 二进制格式我们读不了,
但文本形式可以)。支持 `--ranges`(看翻译窗口)、`--list`(列节点+物理地址)、`--tree`。

---

## 8 现成补丁与工具清单(2026-10-11 二次调查)

把三个项目的**成品**逐个看过。结论:大部分我们能用的东西**上游已经有了**,
真正新的只有一处。

### 8.1 `antiapplefox/m5-linux` —— SPTM 逆向(最深的项目)

| 产物 | 内容 |
|---|---|
| `m1n1-patches/0001~0003` | 加 M4 Pro/Max 和 M5 的 chip ID / MIDR / chickens —— **上游已合并(#629/#578),冗余** |
| `m1n1-patches/0004-sptm-add-xnu-shim-boot-handoff.patch` | **SPTM 的 XNU shim 桩** —— 新的 |
| `linux-sptm/arch/arm64/mm/sptm.c` | Linux 侧的 SPTM 脚手架,~150 行(目标 ~1500–3000 行) |
| `docs/sptm-research.md` | **52 KB 的完整逆向报告** |
| `docs/linux-mmu-port-scope.md` | 22 KB 的移植范围评估 |
| `docs/bootkc-packaging.md` | 怎么把 m1n1 打包成 SPTM 认识的 Boot Kernel Collection |
| `analysis/sptm/*.csv` | 148 个 `(subsys, idx)` 调用号的解码表 |

**关键结论(他们的原话)**

> - SPTM 在 GL2,高于 EL2 —— 高于 OS、高于任何 hypervisor
> - **没有非 XNU 的 supervisor domain** —— `EXEC_MODE_*` 只有
>   `SPTM_DEFAULT` / `TXM_DEFAULT` / `XNU_DEFAULT`。
>   **Linux 必须伪装成 XNU。**
> - iBoot 的 SPTM 初始化**要求内核镜像是形状正确的 BootKC**,否则 panic
> - 各 SoC 拿到 SPTM 的时间:M2 = macOS 15.0,M4 = 出生自带(15.2),
>   **M3 = macOS 26.0**;**M1 (`t8103`) 从来没有**

**状态警示**:他们自己写明 ——
> Patches `0001–0004` apply cleanly and `m1n1.macho` builds, but:
> **runtime-correctness is per static analysis, unverified on hardware**,
> and contingent on m1n1 being packaged as an SPTM-aware BootKC (**not done**).
> **No working shim. No working Linux MMU port.**

**对我们的意义**:这是**内核引导阶段(阶段 4)的路线图**。
ImAtomiskk 在没有它的情况下就把 m1n1 跑起来了,所以 **M1/M2 不需要它**。

### 8.2 `sentaxic/asahi-m5`

| 产物 | 内容 | 可用性 |
|---|---|---|
| `patches/0001-m1n1-t8142-m5-soc-support.patch` | 加 T8142 到 `soc.h`/`smp.c` | ⚠️ **冗余 —— 上游已有** |
| `dts/t8142.dtsi`(5836 B) | 最小设备树 | ⚠️ pre-boot,未验证 |
| `tools/extract_addrs.py` | 从 ioreg dump 提地址表 | ✅ 思路和我们一致 |

### 8.3 ⭐ 唯一真正新的发现:上游 `soc.h` 有个错值

```
上游 m1n1 现状:
  #elif TARGET == T8140 || TARGET == T8142
  #define EARLY_UART_BASE 0x385200000     ← T8140(A18 Pro)的值

sentaxic 的补丁:
  #elif TARGET == T8142
  #define EARLY_UART_BASE 0x3a5200000     ← 和我们的 ADT 一致
```

**核实**:在 J704 的原始 ADT 里搜 `0x385200000` —— **0 命中**。
M5 上只有两个 UART:`uart0 @ 0x3a5200000`、`dockchannel-uart @ 0x388128000`。

**结论:上游给 T8142 的 `EARLY_UART_BASE` 指向一个不存在的地址。**

**影响:低。** 正常构建从 ADT 读地址;只有 `TARGET=T8142` 的"早期调试版"才用这个值。
而 ImAtomiskk 走 USB proxy,根本不经 UART —— 所以没人踩到。

**要用的时候**:本地构建时把那一行改成 `0x3a5200000`(见 sentaxic 的补丁写法)。

### 8.4 `ImAtomiskk/asahim5`

- **m1n1 是 git submodule,指向上游 `AsahiLinux/m1n1`** ——
  **说明上游 m1n1 原样就能在 J704 上跑**,不需要任何补丁
- `dump/` 三份文件(原始 ADT 的 bin / txt / 生成好的 dts)—— **已拿到**
- `notes/` 八份文档 —— **已全部读进 [M1-RUNBOOK](M1-RUNBOOK.md)**

### 8.5 汇总:**我们还需要自己做什么**

| 环节 | 现成的 | 我们要做的 |
|---|---|---|
| 编译/安装 m1n1 | ✅ ImAtomiskk 的完整流程 | 照做 |
| m1n1 支持 T8142 | ✅ 上游已合并 | 无 |
| 抓启动日志 | ✅ 方法已知 | 照做 |
| **修 proxy 基址** | ❌ **没人做成** | ⭐ **从这开始** |
| 原始 ADT | ✅ 已有 | 对账 |
| ADT→DTS | ✅ m1n1 自带 `pmgr_adt2dt.py` | 用它 |
| 内核引导 | ⚠️ 别人"80-90%" | ⭐ **真正的墙** |
| SPTM shim | ⚠️ 有桩,未验证 | 阶段 4 再看 |
