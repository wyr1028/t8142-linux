# M5 / J704 硬件事实

**规则:每条都标来源与置信度。** 未验证的东西必须写明"未验证",不许混进事实里。
来源规则见 [../LEGAL.md](../LEGAL.md),逐条记录见 [PROVENANCE.md](PROVENANCE.md)。

---

## 1 机器

| 项 | 值 | 来源 | 置信度 |
|---|---|---|---|
| 机型 | `Mac17,2` (MacBook Pro 14") | `sysctl hw.model` | 高(直接观测) |
| 芯片 | Apple M5,10 核(4 P + 6 E) | `sysctl` / `system_profiler` | 高 |
| 内存 | 32 GB | `sysctl hw.memsize` | 高 |
| 系统 | macOS 27.0.1 (26A434) | `sw_vers` | 高 |
| 固件 | iBoot/mBoot `20457.1.29` | `system_profiler SPiBridgeDataType` | 高 |
| Secure Boot | **Reduced Security**(SIP 仍开) | 同上 | 高 |
| ADT 根 compatible | `J704AP` / `Mac17,2` / `AppleARM` | `ioreg -a -p IODeviceTree` | 高 |

## 2 SoC 标识

- SoC 前缀 **`t8142`** 贯穿整棵树 → 置信度 **高**
- 板号 **J704** → 置信度 **高**
- 世代序列(从 m1n1 源码读出,公开资料):

  | SoC id | 芯片 |
  |---|---|
  | T8122 | M3 |
  | T8132 | M4 |
  | T8140 | A18 Pro |
  | **T8142** | **M5(base,本机)** |
  | T6050 | M5 Pro |
  | T6051 | M5 Max |
  | T8152 | M6 |

## 3 核名 —— ⚠️ **曾经以为冲突,可能是我看错了**(2026-10-11 更正)

| 来源 | M3 | M4 | M5 |
|---|---|---|---|
| 本机 ADT `compatible` | — | — | `apple,sawtooth` / `apple,everest` |
| m1n1 `midr.h` / `chickens.c` | Sawtooth / Everest | — | 标签写 **"Hidra"** |
| 官方 SoC 代号表(`AsahiLinux/docs`) | Ibiza / **Everest(P) / Sawtooth(E)** | Donan / (核列空) | **Hidra** / (核列空) |

**关键**:官方代号表里 **`Hidra` 是 M5 的「芯片」代号**,而 **`Everest`/`Sawtooth` 是「核」代号**
(表里 M3 那行明确列着)。

所以 m1n1 那行 `"M5 Hidra (E core)"` 是**拿芯片名给核当标签**,
而 ADT 给的是**核代号** —— **两者层面不同,不矛盾**。

**仍未定论的地方**:官方表里 M4/M5 的核列**是空的**,说明还没填。
真要定死,还得真机读 MIDR 对照。**但它不再像之前想的那么"打架"。**

## 4 m1n1 未引用的 M5 compatible

由 `tools/compat_diff.py` 生成 —— 本机 ADT compatible 与某代码库中 `xxx,tNNNN`
字面量的差集。**可复现**:

```bash
python3 tools/compat_diff.py ~/m5-adt.plist <repo>/src --soc t8142
```

> ⚠️ 早期口述的"25 条"是**其中带 `,t8142` 的子集**,不是全部。
> 这个数由脚本给出,不再靠人数。
>
> **用不同来源跑,总数会差 1**(固件版本不同):
> - ioreg(macOS 27.0.1):总数 **39** = t8142 新增 **25** + 复用旧代号 14
> - **我们自己的 ADT**(12661.1.5):总数 **40** = t8142 新增 **25** + 复用旧代号 15
> **"25 个新增"两个来源完全一致**,是稳的。

### 4.1 带 `,t8142` —— 本 SoC 新增,需要新表项(**25 条**)

```
admac,t8142              admac-evolution,t8142   admacled,t8142
apcie,t8142              apciec,t8142
apple-processor-trace,t8142   arm-io,t8142      clpc,t8142
atc-dpin,t8142           atc-dpphy,t8142         atc-dpxbar,t8142
atc-phy,t8142            soc-tuner,t8142         usb-drd,t8142
disp0,t8142              dispext0,t8142          dispext1,t8142
display-crossbar,t8142   dptx-aux,t8142          dptx-ufp-aux,t8142
error-handler,t8142      gpu,t8142               mcc,t8142
pmgr1,t8142              wdt,t8142
```

### 4.2 用旧代代号 —— m1n1 未引用,但硬件疑似与旧 SoC 相同(**14 条**)

```
aes,s8000              aft,t8120             ane,t8132exclave
aod,t8101              avd,t8103             dockchannel,t8002
dptx-core,t8103        event-log-handler,t8101  gpio,t8101
i2c,t8101              jpeg,t8101            scaler,t8101
pcie-apiodma,t6020     pciec-apiodma,t6020
```

> 这一组 m1n1 也没引用,但**不代表不支持** —— 它们用的是旧代代号,通常是
> m1n1 用别的方式处理,或者本来就不归它管。看 `,t8142` 那一组才是真正的新增工作。

其中 **`atc-phy` / `mcc` / `apcie`+`apciec`** 是 m1n1 已为 `t8132`(M4)处理过的同一批块,
增量大概率最小。

## 5 复用旧代号的块(硬件疑似未变)

| compatible | 数量 | 复用自 |
|---|---|---|
| `dart,t8110` | 33 | M1 —— **DART 未变** |
| `avd,t8103` | 1 | M1 —— 视频解码器 |
| `dptx-core,t8103` | 2 | M1 |
| `jpeg,t8101` / `gpio,t8101` / `i2c,t8101` / `scaler,t8101` / `aod,t8101` / `event-log-handler,t8101` | 13 | M1 |
| `dockchannel,t8002` | 1 | |
| `pcie-apiodma,t6020` / `pciec-apiodma,t6020` | 5 | M2 Pro |
| `wlan-pcie,bcm4387` / `bluetooth,n88` | 2 | M1 —— 同无线芯片 |

> 这些是**潜在捷径**:代号没变,通常意味着驱动可以直接复用。

## 6 显示

- base M5 上存在 `disp0` + `dispext0` + `dispext1`,各带独立 `dart-*`、
  `dcp-expert-v1`、以及 `display-crossbar0`
- 过去外接显示块是 Pro/Max 独占 → 若属实,M5 的 die 拓扑更统一
- 置信度:**中**(观测可靠,但"意味着拓扑统一"是推断)

## 7 安全架构(主要障碍)

树中存在:

```
ExclaveOSIntegrityCatalog · ExclaveOSTrustCache · exclave-memory-map · exclaves-test
isp-exclave-proxy · isp-exclave-s-proxy@E1800000 · SPTM-uuid-offset
esm (iop,exclave-sep-manager) · mapper-*-exclave · mapper-sep-exclave
ane,t8132exclave
```

配套未公开代号节点:`sapt` `sacm` `Sandcat` `stockholm` `fillmore` `mesa`
`mogul-las` `avellino-pre` `avellino-post`。

这是 M4+ 世代的主要难点,不是外设数量问题。

## 8 参考规模:M4(t8132)的设备树

从 `AsahiLinux/linux`(分支 `asahi`,`arch/arm64/boot/dts/apple/`)读出:

| 文件 | 规模 | 内容 |
|---|---|---|
| `t8132.dtsi` | 440 行 / 11 KB | 核、timer、aic、pmgr、uart、i2c、pinctrl、wdt、fpwm |
| `t8132-pmgr.dtsi` | **1125 行 / 29 KB / 129 个 power-state** | 大头 |
| `t8132-jxxx.dtsi` | 48 行 | 板级模板 |

M4 板级文件:`-j604 -j623 -j624 -j713 -j715 -j773g`。
**M5(`t8142`)在这些文件里一个都没有。**

---

## 9 ⭐ PMGR 的 `devices` 属性 —— 项目最关键的一块数据

**发现(2026-10-11)**:PMGR 的 power-state **不是设备树里的节点**,而是编码在
`/arm-io/pmgr` 节点的 **`devices` 二进制属性**里(本机 **18576 字节**)。

这直接决定了工具与工作方向:**遍历节点拿不到 power-state,必须解码这个 blob。**

### 9.1 初步观察(置信度:中 —— 字符串可信,结构未定)

- blob 内含 NUL 结尾的名字字符串,已抽出 **335 个唯一名字**
- 条目疑似**定长**;名字出现在固定偏移(前两个名字在字节 32 与 84,间距 52)
- 名字样例:`ACTIVE` `ECPU_0` `AMCC0_P0..P3` `ANE_CPU` `AOP_BASE`
  `AOP_DART` `AOP_GPIO` `AOP_I2CM0..3` …
- 命名规律像 `块_子单元`

### 9.2 ⚠️ 与 M4 的对照别搞错口径

| | 数量 | 含义 |
|---|---|---|
| M4 的 `t8132-pmgr.dtsi` | **129 条** | Linux **需要**的子集 |
| 本机 `devices` blob 抽出的名字 | **335 个** | PMGR **全量**设备表 |
| m1n1 在 M4 Pro 上枚举 | 485 个 / 单 die | PR #578 的实测值 |

**三者口径不同,不能直接相减。** 想回答"能复用多少",必须先把口径对齐。

### 9.3 为什么这条最重要

它是"**M5 的 PMGR 和 M4 差多少**"这个问题的唯一数据源 —— 而这个问题
决定项目是**月级**还是**年级**([ROADMAP](../ROADMAP.md) 阶段 3)。

而且:**现在就能做,不用等真机。** ioreg 已经把这段二进制属性原样带出来了。

**下一步**:读 m1n1 的 `src/pmgr.c`(公开 GPL,读它合法)搞清条目格式,
写 `tools/pmgr_devices.py` 解码,产出 M5 的 power-domain 清单,再与 M4 逐条比。

---

## 附:本地数据文件

| 文件 | 说明 |
|---|---|
| `~/m5-adt.plist` | 原始 `ioreg` dump(2.4 MB)—— **含序列号 / UUID / MAC / nonce,禁止外发** |
| `~/m5-adt-topology.txt` | 洗过的拓扑,527 节点,已核验序列号 0 命中 |
| `~/m5-adt-report.md` | 分析报告(v2) |

采集时间:2026-10-11。

> ⚠️ **注意**:上面这些是 **macOS 过滤视图**(`ioreg` 的 IODeviceTree 平面),
> **不是原始 ADT**。原始 ADT 必须靠 m1n1 上机 dump。见 [../ROADMAP.md](../ROADMAP.md) 阶段 1-2。
