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

## 3 三个必须先答的问题

### 3.1 ⚠️ `reg` 的 cell 格式对不上(**最卡的一个**)

```
M4 的 DT:  reg = <0x3 0x80700000 0 0x14000>        ← (hi, lo, size_hi, size_lo)
M5 的 ADT: reg =  70700000  1       d0000  0       ← 第二个 cell 恒为 1
```

M5 那 14 个节点的**第二个 cell 全是 `0x1`**,所以它不像"地址高 32 位",
更像一个常量标志。两种可能:

- ADT 布局是 `(addr, flags, size, flags2)`,地址只有低 32 位 → M5 的 DT 该写 `<0 0x70700000 0 0xd0000>`
- 或者高 32 位真的是 `0x1`,M5 的外设空间整体落在 `0x1_7xxxxxxx`

**不解决这个,写出来的每个 `reg` 都可能错。**

### 3.2 CPU 的 compatible 叫什么

三个来源打架(见 [HARDWARE.md §3](HARDWARE.md)):

| 来源 | M4 | M5 |
|---|---|---|
| Linux DTS | `apple,donan-e` / `apple,donan-p` | — |
| m1n1(读真 MIDR) | — | **Hidra** |
| 本机 ADT | — | `apple,sawtooth` / `apple,everest`(M3 的名字) |

还有 CPU 的 `reg`:M4 的 P 核是 `0x10100`,M5 的 ADT 显示 `cpu@100`。**也是不一致的。**

### 3.3 AIC 的中断号

M4 的 DT 写符号表 `AIC_IRQ 1046`。M5 的中断号在 ADT 的 `interrupts` 属性里,
**可解码**(格式待定)。

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

**M5 到"串口出字"的距离,比想象近得多:**

```
t8142.dtsi        ~440 行结构,照抄 M4,地址换 M5 的   ← 堵在上面 3.1
t8142-pmgr.dtsi   已生成(135 条,dtc 通过)            ← 完成
t8142-jxxx.dtsi   ~48 行 boilerplate                  ← 待做
t8142-j704.dts     ~35 行                              ← 待做
```

**卡点不是"工作量",是"三个格式问题"。**
其中 3.1 大概率能在真机上半小时内问清楚(写一下看能不能工作);3.2、3.3 同理。

**这就是为什么下一步是机器,不是更多纸面分析。**
