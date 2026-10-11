# 操作手册(M0 → M7)

> 每一步写清:**做什么 / 具体命令 / 判据 / 失败了怎么办**。
> 不确定的地方标 ⚠️,**不许猜**。命令里 `<...>` 是要你替换的。
>
> 权威参考(公开文档,读它合法):
> - m1n1 User Guide — https://asahilinux.org/docs/sw/m1n1-user-guide/
> - m1n1 源码自带的 README
>
> ⚠️ 拉任何上游仓库之前,**先读它的 `AGENTS.md` / `CLAUDE.md`** —— 本项目只读不改。

---

## 阶段 0 · 前置采购清单(一次性)

| 项 | 要求 | 备注 |
|---|---|---|
| 第二台机器 | 能跑 USB 的 **Linux** 最佳;Apple Silicon Mac 次之 | Mac 也能用,但要装 Apple Configurator 做兜底 |
| USB-C 线 | **必须是数据线**,不是只充电的线 | 这条最容易踩,充电线接上去什么都看不见 |
| 备份 | M5 上一份完整备份 | Time Machine 即可 |
| 时间 | 预留一整个下午 | 中途卡住很正常,别赶时间 |

**为什么第二台机器必须是 Linux**:tethered boot 期间,它要通过 USB 跟 M5 上的 m1n1 对话(device-mode USB),还要跑交叉编译。Mac 也能做(M 系列可原生编译),但 Linux 的工具链更省事。

---

## 阶段 1(M0)· 第二台机器就位

### 1.1 装工具链

**Debian / Ubuntu:**

```bash
sudo apt update
sudo apt install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
                 make git python3 python3-pip picocom libusb-1.0-0-dev
```

**Fedora:**

```bash
sudo dnf install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
                 make git python3 picocom libusb1-devel
```

**Apple Silicon Mac(原生编译,不需要交叉工具链):**

```bash
brew install make python3
rustup target add aarch64-unknown-none-softfloat   # m1n1 有 Rust 部分
```

### 1.2 判据

```bash
aarch64-linux-gnu-gcc --version    # Linux
# 或 Mac 上:
rustup target list --installed | grep none-softfloat
```

**两条都通不了就停下**,先解决这两个,别往下走。

### 1.3 插上 USB-C 线,确认不是哑线

```bash
lsusb                              # Linux
```
插拔 M5 侧(此时 M5 正常开机的 macOS 状态),看 `lsusb` 有没有变化。没变化 → 换线。

---

## 阶段 2(M1)· 点亮 m1n1

> ⚠️ **这一步会改 M5 的 boot policy。** 没有第二台机器兜底不要做。

### 2.1 先看现状(在 M5 的 macOS 里)

```bash
system_profiler SPiBridgeDataType | grep -A6 "Boot Policy"
```

期望:`Secure Boot: Reduced Security`(本机已确认)。若还是 Full Security,先降到 Reduced。

### 2.2 编译 m1n1(在第二台机器上)

```bash
git clone https://github.com/AsahiLinux/m1n1.git
cd m1n1
# ⚠️ 先读 AGENTS.md / CLAUDE.md,然后什么都不改
make
```

产物:
- macOS ≥ 12.1 → `build/m1n1.bin`
- 更老 → `build/m1n1.macho`(国内机器用不到)

### 2.3 把 m1n1.bin 弄到 M5 上

1TR 环境里有网络和 `curl`,也可以走 U 盘。**二进制别用聊天软件传**(会被改)。

### 2.4 进 1TR

1. M5 关机
2. **按住电源键不松**,直到屏幕出现「**正在载入启动选项**」(Loading startup options)
3. 松开,选「**选项**」(Options)→ 进恢复环境
4. 菜单栏「**实用工具**」→「**终端**」

现在你就在 1TR 里了。

### 2.5 降安全(在 1TR 的终端里)

```bash
bputil -nkcas
csrutil disable          # bputil 会重置 SIP,所以放在后面做
```

> ⚠️ `bputil -nkcas` 的参数含义以 `bputil --help` 为准,别照抄。这一步改的是**下一次启动**的策略。
> 报错的话:先 `csrutil clear`,重启回 1TR,再来一遍。

重启,重新进 1TR(2.4 重做一次)。

### 2.6 装 m1n1 作为启动对象

**先把目标卷设成默认启动磁盘**,再:

```bash
kmutil configure-boot -c m1n1.bin \
    --raw --entry-point 2048 --lowest-virtual-address 0 \
    -v <目标卷的挂载路径,如 /Volumes/macOSTest>
```

> ⚠️ **卷的选择是最容易出错的地方。** 文档明确:必须在**目标 OS 自己的恢复环境**里跑,
> 否则报 `not paired`。本机没装 Asahi,所以要自己规划一个卷(通常是一个小的独立 APFS 卷
> 当 stub)。**具体怎么规划,读 m1n1 User Guide,别照我这句猜。**

### 2.7 启动

重启 → 按住电源键 → 启动选项里应多出一个入口 → 选它。

### 2.8 判据

m1n1 起来后,在第二台机器上连接它的 proxy:

```bash
cd m1n1
python3 proxyclient/...        # 具体入口看仓库 README 与 user guide
```

**能拿到交互提示符 = 成功。**

### 2.9 失败对照表

| 现象 | 原因 |
|---|---|
| `not paired` | 不是目标 OS 自己的 recovery |
| `Fileset Error: Invalid Mach-O boot properties` | 目标卷不是默认启动磁盘 |
| 完全没有新启动项 | `kmutil` 没成功写入,回 2.6 |
| 启动项出现但一选就黑屏重启 | 记串口输出,这是**有价值的失败报告** |

---

## 阶段 3(M2)· 采集原始 ADT

在 m1n1 的交互 shell 里 dump 设备树(命令名以 user guide 为准),把结果落盘。

**必须做**:

1. 在 [PROVENANCE.md](PROVENANCE.md) 记一行:m1n1 的 commit hash + 命令 + 结果
2. 存成 `raw-adt.dtb`(⚠️ 进 `.gitignore`,不进版本库)
3. 跑一遍工具验证读得动:

```bash
python3 tools/adt2dts.py raw-adt.dtb --out /tmp/check.dts
python3 tools/compat_diff.py raw-adt.dtb <某仓库>/src --soc t8142
```

**判据**:`adtlib.load()` 能读出原始 ADT,节点数 ≥ 527(macOS 视图是过滤过的,原始应当更多)。

---

## 阶段 4(M3)· 摸清 M5 vs M4 的差异 —— **决定成败**

这一步决定项目是**月级**还是**年级**。全部产出写进 `docs/PMGR-DELTA.md`。

### 4.1 PMGR(最重要)

- 在 m1n1 里看它枚举出多少个 pmgr device(参考:M4 Pro 上是 485 个 / 单 die)
- 拉 M4 的 `t8132-pmgr.dtsi`(129 条 power-state),逐条比
- **回答一个问题:129 条里能原样复用几条?**

### 4.2 核名冲突

见 [HARDWARE.md §3](HARDWARE.md)。三个来源打架,必须在真机上定性:
- 读实际 MIDR,确认 part 号
- 确认 DTS 里 CPU `compatible` 该写什么

### 4.3 其余增量

- AIC v3(`aic,3` vs M3 的 `apple,t8122-aic3`)
- DART:`dart,t8110` 是否真的零改动
- PCIe / USB:对比 `t8142` 与 `t8132` 的 reg 布局

**判据**:能写下"复用率 X%"并给出依据。

---

## 阶段 5(M4)· 生成设备树骨架

```bash
python3 tools/adt2dts.py raw-adt.dtb --out dts/t8142-full.dts
python3 tools/adt2dts.py raw-adt.dtb --prefix /arm-io/pmgr --out dts/t8142-pmgr.dtsi
python3 tools/adt2dts.py raw-adt.dtb --compatibles-only > docs/compatibles.txt
```

产出的骨架**不能编译**,只提供形状。人工补:`interrupt-parent` / `clocks` / `power-domains` / `iommus` / `#address-cells`。

---

## 阶段 6(M5)· 写设备树

| 文件 | 参照 | 说明 |
|---|---|---|
| `dts/t8142.dtsi` | `t8132.dtsi`(440 行) | 核、timer、aic、pmgr、uart、i2c、pinctrl、wdt |
| `dts/t8142-pmgr.dtsi` | `t8132-pmgr.dtsi`(1125 行) | **大头**,按阶段 4 的结论改 |
| `dts/t8142-j704.dts` | `t8132-jxxx.dtsi`(48 行) | 板级 |

**编译验证**:在内核树里 `make ARCH=arm64 dtbs`。**能编过**是本阶段判据。

---

## 阶段 7(M6)· 引导内核 —— 第一个真实成果

- 内核:`Image` + `t8142-j704.dtb`
- 通过 m1n1 chainload 喂进去
- 串口应出现内核日志

**判据**:**屏幕(串口)上出现一行内核 printk。**

到这一步,你已经比绝大多数人走得远了。之后才是 NVMe、多核、显示……

---

## 阶段 8(M7)· 之后

按 [ROADMAP.md](../ROADMAP.md) 阶段 7 走。顺序建议:
无线(`bcm4387`,可能与 M1 同款,直接可用)→ USB → 显示 → 音频 → 电源管理。

⛔ **GPU 不要计划**。

---

## 附录 · 每次都做的三件事

1. **动手前**:确认这一步会不会砖机器,有没有兜底
2. **动手后**:往 [PROVENANCE.md](PROVENANCE.md) 记一行(谁、在哪台机器、跑了什么)
3. **下结论前**:问"这是观测还是推断?"推断必须标出来

### 兜底:真把机器搞砖了

需要**另一台 Mac** + USB-C 线 + Apple Configurator,把 M5 进 DFU 模式恢复。
这就是为什么阶段 0 里"第二台机器"是硬前置。
