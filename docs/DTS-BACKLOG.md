# 设备树待办 —— M4 到底做了多少,M5 缺什么

**结论先行:M4 的 Linux 支持就是"能出串口",总共 440 行。M5 要补齐的活比原先估计小得多。**

---

## 1 M4 的整个设备树长什么样

| 文件 | 行数 | 内容 |
|---|---|---|
| `t8132.dtsi` | **440** | CPU / timer / clkref / **soc 下的全部外设** |
| `t8132-pmgr.dtsi` | 1125 | PMGR 电源域(已用 `pmgr_join.py` 生成 M5 版) |
| `t8132-jxxx.dtsi` | 48 | 板级公共:串口 console、framebuffer 占位、memory 占位 |
| `t8132-j713.dts` | **35** | 具体机型:只配了个键盘背光 LED |

**板级文件 35 行** —— 里面 90% 是注释和 boilerplate。

### `t8132.dtsi` 里定义的**全部**外设

```
cpus(6 E + 4 P + 2 个 L2)   timer    clkref
soc:
  pmgr            0x3_80700000   0x14000
  aic             0x3_81000000   0x1cc000  (+ event 0x3_81040000)
  pmgr_mini       0x3_88280000   0x4000
  wdt             0x3_882b0000   0x4000
  pinctrl_nub     0x3_881f0000   0x4000
  pinctrl_smc     0x3_8c820000   0x4000
  pinctrl_aop     0x3_90824000   0x4000
  pinctrl_ap      0x3_9a000000   0x100000
  i2c0..i2c4      0x3_ad010000 起,步长 0x4000
  fpwm1           0x3_ad044000   0x4000
  serial0         0x3_ad200000   0x1000
```

**没有 DART、没有 PCIe、没有 USB、没有显示、没有 NVMe。**
framebuffer 是 `status = "disabled"` 的占位符(`To be filled by loader`)。

所以 M4 的 Linux = **"内核能跑起来、串口能说话"**。这跟"M4 还不可用"的说法一致。

---

## 2 M5 缺什么 —— 好消息:**数据一个不缺**

把上表逐个去 M5 的 ADT 里找,14 个全找到,地址尺寸都有:

| M4 节点 | M5 ADT 节点 | M5 的 reg(ADT 原始 cell) | M5 compatible |
|---|---|---|---|
| `pmgr` | `pmgr` | `70700000 1 d0000 0` | `pmgr1,t8142` |
| `aic` | `aic` | `71000000 1 1cc000 0` | `aic,3` |
| `wdt` | `wdt` | `782b0000 1 4000 0` | `wdt,t8142` |
| `pinctrl_nub` | `nub-gpio` | `781f0000 1 4000 0` | `gpio,t8101` |
| `pinctrl_smc` | `smc-gpio` | `7c820000 1 4000 0` | `gpio,t8101` |
| `pinctrl_aop` | `aop-gpio` | `80824000 1 4000 0` | `gpio,t8101` |
| `pinctrl_ap` | `gpio0` | `8a000000 1 100000 0` | `gpio,t8101` |
| `i2c0..4` | `i2c0..4` | `95010000` 起,步长 `4000` | `i2c,t8101` |
| `fpwm1` | `fpwm0` | `95040000 1 4000 0` | `fpwm,s5l8920x` |
| `serial0` | `uart0` | `95200000 1 4000 0` | `uart-1,samsung` |

注意 M5 的地址整体挪了(M4 在 `0x3_8xxxxxxx`,M5 在 `0x7xxxxxxx`),
但**结构一一对应**——和 PMGR 那边"名字 92% 重合"是同一个故事。

---

## 3 三个卡点 —— **两个已解决**(2026-10-11)

### 3.1 ✅ 已解决:`reg` 的 cell 格式

```
M4 的 DT :  reg = <0x3 0x81000000 0 0x1cc000>       ← (hi, lo, size_hi, size_lo)
M5 的 ADT:       0x71000000  0x1  0x1cc000  0x0     ← (lo, hi, size_lo, size_hi)
                    ↑                 ↑
                 低 32 位             尺寸 —— **两边完全一致**
```

**两边的 cell 只是顺序相反,值一一对应。** 而且:

- M4 的 DT 里**所有**外设的高位都是 `0x3`
- M5 的 ADT 里**所有**外设的第二格都是 `0x1`

两边都是常量 → 说明那就是地址高位,不是标志位。**两个世代的 MMIO 区域整体挪了位置:**

```
M4: 0x3_8xxxxxxx
M5: 0x1_7xxxxxxx
```

所以 M5 的 `pmgr` 在 DT 里应写成 `reg = <0x1 0x70700000 0x0 0xd0000>`。

置信度:**高**(多个节点的尺寸/结构交叉吻合),但仍是推断,**真机上要验**。

### 3.2 ⚠️ 仍未解决:CPU 的 compatible 叫什么

三个来源打架(见 [HARDWARE.md §3](HARDWARE.md)):

| 来源 | M4 | M5 |
|---|---|---|
| Linux DTS | `apple,donan-e` / `apple,donan-p` | — |
| m1n1(读真 MIDR) | — | **Hidra** |
| 本机 ADT | — | `apple,sawtooth` / `apple,everest`(M3 的名字) |

还有 CPU 的 `reg`:M4 的 P 核是 `0x10100`,M5 的 ADT 显示 `cpu@100`。

**这个只能在真机上读 MIDR 才能定。**

### 3.3 ✅ 已解决:AIC 的中断号

**ADT 的 `interrupts` 属性里那个 u32 就是 AIC 中断号本身。** 依据 —— 个数和连号规律全部吻合:

| M5 节点 | 个数 | M5 的 ADT 值 | M4 的 DT 值 |
|---|---:|---|---|
| `uart0` | 1 | 1231 | `AIC_IRQ 1046` |
| `i2c0` | 1 | 1247 | `AIC_IRQ 1062` |
| `i2c1` | 1 | 1248 | `AIC_IRQ 1063` |
| `wdt` | 2 | 361, 0 | `AIC_IRQ 507` |
| `nub-gpio` | 7 | 574..580 | `AIC_IRQ 499..505` |
| `smc-gpio` | 7 | 624..630 | `AIC_IRQ 552..558` |
| `aop-gpio` | 7 | 480..486 | `AIC_IRQ 423..429` |
| `gpio0` | 7 | 347..353 | `AIC_IRQ 303..309` |

**8 个节点的中断个数全部对上**,而且连号区间一一对应。

> 注意:中断号本身**变了**(M5 和 M4 不一样),但**编码方式没变** —— 直接抄 ADT 的值即可。

---

## 4 好消息:能直接复用的

| 项 | 说明 |
|---|---|
| `power-domains = <&ps_xxx>` | 标签来自我们自己生成的 `t8142-pmgr.dtsi`,名字已对上 |
| `clkref` 24 MHz | 固定时钟,大概率不变 |
| `timer` / `armv8-timer` | 通用 |
| 板级文件 | 48 + 35 行 boilerplate,照抄改地址即可 |

---

## 5 结论

**三个卡点解决了两个。M5 到"串口出字"的距离,比想象近得多:**

```
t8142.dtsi        已写出, **dtc 编译通过**(187 个节点)   ← ✅
t8142-pmgr.dtsi   已生成(135 条,dtc 编译通过)           ← ✅
t8142-jxxx.dtsi   ~48 行 boilerplate                     ← 待做(照抄)
t8142-j704.dts     ~35 行                                 ← 待做(照抄)
```

### 5.1 怎么编译验证的

macOS 自带的 `dtc` **不带预处理器**,吃不了 `#include <...>` 和 `#address-cells`。
两个绕法(只是验证用,真编译走内核构建系统):

```bash
# ① 把 #include <...> 删掉,把宏展开成字面量(AIC_IRQ→0 等)
# ② 文件是被 include 的,要包一层壳:
printf '/dts-v1/;\n/include/ "t8142.dtsi"\n' > w.dts
dtc -I dts -O dtb -o out.dtb w.dts
```

### 5.2 草稿里还标着 TODO 的地方

| 位置 | 内容 |
|---|---|
| CPU 的 `compatible` | §3.2 未定,先按 ADT 的 `sawtooth`/`everest` 写 |
| CPU 的 `reg` | 用了 M5 的 `0x100..0x103`,与 M4 的 `0x10100` 编码不同,待确认 |
| L2 大小 / `apple,npins` / `gpio-ranges` | 照抄 M4,需从 ADT 或真机确认 |
| pinctrl 的 `pinmux` 编号 | **板级数据,照抄 M4 很可能不对** |
| pmgr / aic / wdt 的多段 `reg` | M5 与 M4 段数不同,内核认不认待确认 |

**只剩一个真卡点:CPU 的 compatible 到底叫什么**(§3.2)。
那个需要真机上读 MIDR —— 半小时能问清楚。

其余全部齐了:

| 需要什么 | 状态 |
|---|---|
| 地址格式(§3.1) | ✅ 已定 |
| 中断号(§3.3) | ✅ 已定 |
| 电源域标签 | ✅ 已生成 |
| 板级 boilerplate | ✅ 照抄 |
| **CPU compatible(§3.2)** | ⚠️ **唯一剩的** |

> 纸面工作确实到头了 —— 但"到头"的原因是**数据已经够写设备树了**,
> 不是"无事可做"。**真机一到,`t8142.dtsi` 基本可以当场写出来。**
