# 工作清单

`[ ]` 待做 · `[x]` 完成 · `[!]` 阻塞中 · `[~]` 进行中

---

## 阶段 0 · 前置硬件 —— `[!]` 当前阻塞点

- [ ] **找到/搬来一台能连 USB-C 的第二台机器**(Linux 最好;Mac 也行,兼作 DFU 恢复兜底)
- [ ] 第二台机器上装 aarch64 交叉工具链(`aarch64-linux-gnu-gcc`)
- [ ] 备份这台 M5 的重要数据(Time Machine)
- [x] 确认 Secure Boot 状态 → **Reduced Security**(2026-10-11)

> ⚠️ **没有第二台机器兜底,不要动 boot policy。** 这是唯一可能真出事的地方。

**判据**:第二台机器就位 + 交叉工具链可用。

---

## 阶段 1 · 点亮 m1n1

- [ ] 拉 m1n1 源码
  - **先读仓库根的 `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`** —— 见 [LEGAL.md](LEGAL.md) 黄线
- [ ] 编译 m1n1
- [ ] 进 1TR,装 stub
  - macOS ≥ 12.1:
    `kmutil configure-boot -c m1n1.bin --raw --entry-point 2048 --lowest-virtual-address 0 -v <OS 卷>`
  - 只用 Apple 提供的通道,不绕过签名
- [ ] 建立连接(设备模式 USB 或串口,`picocom`)
- [ ] **拿到 m1n1 proxy**

**判据**:m1n1 起来,能看到 ADT。

---

## 阶段 2 · 采集原始数据

- [x] macOS 侧的 ADT 视图(`ioreg` 的 IODeviceTree 平面)—— 2026-10-11
- [ ] **dump 真正的原始 ADT**(不是 macOS 过滤视图)
- [ ] 记进 [docs/PROVENANCE.md](docs/PROVENANCE.md):哪台机器、哪个 commit、什么命令
- [ ] 记录 m1n1 枚举出的 PMGR device 数量与清单

**判据**:拿到原始 ADT blob,并已归档来源。

---

## 阶段 3 · 摸清 M5 与 M4 的差异 —— **决定成败**

> 这一阶段决定项目是**月级**还是**年级**。

- [ ] 对比 `t8142` 与 `t8132`(M4)的 PMGR 布局
- [ ] 定性**核名冲突**([docs/HARDWARE.md §3](docs/HARDWARE.md))
- [ ] 确认 AIC v3 的增量(`aic,3` vs M3 的 `apple,t8122-aic3`)
- [ ] 确认 DART(`dart,t8110` 复用是否真的零改动)
- [ ] 确认 PCIe / USB 的增量

**判据**:能明确回答 —— **"129 个 power-state 能复用多少?"**

- 复用率高 → 几周到几个月能到串口
- 复用率低 → 每条都要从真机读出来,年级

---

## 阶段 4 · 工具(不吃硬件,可现在做)

- [ ] **写 ADT → DTS 生成器**(`tools/adt2dts.py`)
  - 输入:原始 ADT dump
  - 输出:`t8142.dtsi` / `t8142-pmgr.dtsi` 骨架
  - 理由:别手抄 129 条 power-state
- [ ] 写 compatible diff 脚本(复现 §4 那 25 个的推导过程)
- [ ] 写 M4 → M5 节点对照表生成器

---

## 阶段 5 · 设备树

- [ ] `dts/t8142.dtsi` —— 核、timer、aic、pmgr、uart、i2c、pinctrl、wdt、fpwm
      (参考 `t8132.dtsi`,440 行)
- [ ] `dts/t8142-pmgr.dtsi` —— **大头**,预计 1000+ 行
- [ ] `dts/t8142-j704.dts` —— 板级,~48 行
- [ ] 确认 CPU 节点的 `compatible` 写法(等阶段 3 定性)

---

## 阶段 6 · 内核引导

- [ ] **串口 console 有输出** ← **第一个真实里程碑**
- [ ] 多核启动
- [ ] NVMe + 挂上 rootfs

---

## 阶段 7 · 外设(远期)

- [ ] 显示(`disp0` / `dispext0` / `dispext1` / `display-crossbar`)
- [ ] USB(`atc-phy` / `usb-drd` / `atc-dpxbar`)
- [ ] Wi-Fi / BT(`wlan-pcie,bcm4387` / `bluetooth,n88` —— 与 M1 同款,**可能直接可用**)
- [ ] 音频(`admac,t8142` 一族)
- [ ] 视频解码(`avd,t8103` —— 复用 M1 代号,可能直接可用)
- [ ] 电源管理 / 调频(`clpc,t8142` / `soc-tuner,t8142`)

> ⛔ **GPU 不要计划。** `gpu,t8142` 是全新代次,Asahi 在这块花了数年且是团队规模。
> 单人做这个没有意义。

---

## 待定问题(必须先回答,否则设计会错)

1. **M5 的核 compatible 到底叫什么?** 三个来源打架 —— `sawtooth/everest`(ADT)
   vs `Hidra`(MIDR) vs M4 用 `donan`。见 [docs/HARDWARE.md §3](docs/HARDWARE.md)。
2. **M5 的 PMGR 与 M4 差多少?** 整个项目的成败押在这。
3. **base M5 真的有三个显示控制器吗?** 若属实可能省掉一套 die 分支。

---

## 里程碑速览

```
M0  第二台机器 + 交叉工具链                      ← 现在卡在这
M1  m1n1 点亮,能看 ADT
M2  原始 ADT 归档
M3  M5 vs M4 差异定性            ← 决定月级还是年级
M4  ADT→DTS 生成器跑通
M5  t8142*.dts* 写完
M6  串口有输出                   ← 第一个真实成果
M7  多核 + NVMe + rootfs
M8+ 显示 / USB / 无线 ...
```
