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

### 1.1 最值得看的两份

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

**坏消息 / 真难点**

- **AICv3 是硬骨头** —— 不在"照抄 M4"的范畴里,需要真写代码
- 我们的机器(J704)**没人跑过**
- 那两份现成设备树**互相打架**(serial / i2c 的地址对不上),都需要真机验证

**所以结论修正**:不是"月级"那么轻松 —— **AICv3 这一关是实打实的**。
但也不是年级:内核、驱动、绝大多数块都能复用,真正要新写的主要就是 AIC。

---

## 5 下一步(待真机)

1. 拿到**原始 ADT**(M2)—— 才能确认窗口规则和 AIC 的真实寄存器布局
2. 跑通 m1n1(M1)—— m1n1 对 `aic,3` 的态度要先确认
3. 决定 AICv3 怎么处理 —— 这是本项目**唯一确定要新写的驱动**

---

## 附:引用来源

- `AsahiLinux/linux` commit `76db823`(rhelvista,2026-07-18)
- `sentaxic/asahi-m5`(README / `docs/T8142-SOC.md` / `docs/address-map.txt`)
- m1n1 PR #629 / #578
- Asahi Linux Linux 7.2 进度报告
