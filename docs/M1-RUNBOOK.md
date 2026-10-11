# M1 操作手册:点亮 m1n1

> **这一步会改 M5 的 boot policy。** 前面三样准备(备份已验证 / DFU 兜底就位 / 数据线验过)
> 就是为了这里。
>
> 不确定的地方标 ⚠️,**不猜**。带 ⚠️ 的步骤必须先去读权威文档。

---

> # ✅ 2026-10-11:流程已由**同一台机器**上的项目实测过
>
> `ImAtomiskk/asahim5`(J704,和你**同一台**)已经把 M1 走通了,并留下了完整流程。
> **下面从 ③ 起,以他们的实测步骤为准**,我原来的推断作废(尤其 ⑤ 那步)。
>
> 他们的实测结果:**m1n1 编译 ✔ 安装 ✔ proxy 模式 ✔ dump 文件 ✔**,
> **hypervisor 模式 ✔**,Linux 启动"约 80-90%"。
>
> 新增的、我原来完全不知道的三条:
> - **FileVault 必须先关**(见 §0b)
> - **1TR 的硬判据:工具菜单里要有「恢复助理」**
> - **`-v` 他们直接指向 macOS 数据卷**(`/Volumes/Macintosh HD - Data`),不是 stub 卷

---

## 0b ⚠️ 我原来漏了:先关 FileVault

系统设置 → 隐私与安全性 → FileVault → **关掉**。

> 不关的话,后面 m1n1 装上去可能起不来。**这一条我前面完全没提。**

---

## 0 开始之前

- [ ] 游戏本的 Ubuntu 装好,`bash tools/check_host.sh` **全绿**
- [ ] M5 备份已验证(做过了 ✅)
- [ ] M3 MacBook Air 上 Apple Configurator 2 就位(做过了 ✅)
- [ ] 数据线验过(做过了 ✅)
- [ ] **M5 上该存的东西存好**

---

## 全程概览

```
① 在 Linux 主机上编译 m1n1
② 把 m1n1.bin 弄到 M5
③ M5 进 1TR
④ 降安全
⑤ 装启动对象          ← ⚠️ 卡点,必须先读文档
⑥ 重启,选 m1n1
⑦ 建连接              ← 判据在这里
```

---

## ⚠️ 先明确:这一步改了什么持久状态

| 改了什么 | 怎么回退 |
|---|---|
| `bputil` 降了安全策略 | 再进 1TR 跑 `bputil`,或恢复出厂策略 |
| `csrutil` 关了 SIP | `<在恢复环境里>` `csrutil enable` |
| `kmutil` 写入了自定义启动对象 | 再跑一次 `kmutil configure-boot` 覆盖掉 |

**都是可逆的,但都要你主动去退。**

---

## 🎬 先看一遍全程:实际是什么体验

**别把 m1n1 想成"装了个系统"。它是这个:**

> **一个跑在 M5 上的小程序,通过 USB 线,给你一台 Linux 笔记本上的命令行。**

### 你会看到的画面

```
【游戏本 · 终端】                    【M5 · 屏幕】
   │                                    │
   │  敲 make,编出 m1n1.bin              │  (正常用 macOS)
   │                                    │
   │                                    │  关机 → 按住电源键
   │                                    │  → 选「选项」进恢复环境
   │                                    │  → 终端里敲几条命令
   │                                    │
   │                                    │  重启 → 选新出现的启动项
   │                                    │  ↓
   │                                    │  屏幕可能黑着,也可能出
   │                                    │  一个很简陋的文字界面
   │                                    │  ⚠️ 不确定,别指望它
   │  /dev/ttyACM0 出现 ←────────────────┤  ← 这时 USB 通道建起来了
   │  用 picocom 连上去                    │
   │  ↓                                   │
   │  ╔══════════════════════════╗        │
   │  ║ m1n1 的提示符             ║        │
   │  ║ > _                      ║        │
   │  ╚══════════════════════════╝        │
```

**关键认知:你要盯着的是「游戏本的终端」,不是 M5 的屏幕。**

M5 的屏幕到时候可能什么都不显示 —— 这不代表失败。m1n1 的主通道是那根 USB 线。

### 那个提示符下你能干什么

它像个简陋的 shell。**进去第一件事敲 `help`。** 大致能做这几类事:

| 能干什么 | 用来做什么 |
|---|---|
| **看设备树** | dump 出**原始 ADT** —— 这就是 M2 的全部目的 |
| **读内存 / 寄存器** | 真机验证:看某个地址上到底有什么 |
| **引导 payload** | 把编译好的内核喂进去启动(Tethered Boot) |
| **跑脚本** | m1n1 带一个 Python 客户端,可以写脚本跟它对话 |

### 之后每一步长什么样

```
M1  看到提示符          ← 一次性的,过了这关就永远有
M2  敲命令 dump 设备树   ← 拿到 .dtb 文件,存到游戏本上
M3  跑我们的工具分析      ← 在游戏本上,不需要碰 M5
M4  生成设备树           ← 在游戏本上
M5  补设备树             ← 在游戏本上
M6  把内核喂进去,串口出字 ← 回到 M5 上操作
```

**注意 M2 到 M5 全在游戏本上做**,M5 只是待机(或者回 macOS 正常用)。
**只有 M1 和 M6 需要动 M5 的启动。**

### 一次 M1 大概要多久

如果一切顺利:**一小时以内**。卡人的通常是第 ⑤ 步(卷怎么规划)。

---

## ① 编译 m1n1(在 Linux 主机上)

**macOS 上也能编**(他们实测的依赖):

```bash
brew install make python3 gcc-aarch64-embedded
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1 && make -j$(sysctl -n hw.ncpu)
```

**Ubuntu 上:**

```bash
sudo apt install build-essential git python3 python3-pip gcc-aarch64-linux-gnu
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1 && make -j$(nproc)
```

> ⚠️ **两个产物都要**:**`.macho` 用于安装,`.bin` 用于 proxy/hypervisor 模式。**

**判据**:`build/` 下同时出现 `m1n1.macho` 和 `m1n1.bin`。

编译失败先解决编译,别往下走 —— 报错贴给我。

---

## ② 把 m1n1.bin 弄到 M5

U 盘、`scp`、网盘都行。

> ⚠️ **别用聊天软件传二进制** —— 可能被改。

传完在 M5 上确认大小对得上:

```bash
ls -l ~/Downloads/m1n1.bin
```

---

## ③ M5 进 1TR

1. **关机**(彻底关,不是睡眠)
2. **按住电源键不松**,直到屏幕出现「**正在载入启动选项**」
3. 松开,选「**选项 / Options**」
4. 进恢复环境后,顶部菜单栏 → 「**实用工具**」→「**终端**」

现在你在 1TR 里了。**接下来所有命令都在这个终端里敲。**

---

## ④ 降安全

```bash
bputil --help          # ⚠️ 先看一遍参数含义,别照抄下面的
bputil -nkcas
```

> ⚠️ `-nkcas` 这几个字母的含义**以 `--help` 为准**。改的是**下一次启动**的策略。
> 报错的话:先 `csrutil clear`,重启回 1TR,再来一遍。

然后:

```bash
csrutil disable        # bputil 会重置 SIP,所以放后面
```

**重启,重新进 1TR**(第 ③ 步重做一遍)。

---

## ⑤ 装启动对象

> ⚠️ **下面的流程来自公开文档的搜索引擎摘要,不是官方页面原文**
> (asahilinux.org 在我这边的网络取不到)。
> **动手前务必对照原文核对:**
> - m1n1 User Guide — https://asahilinux.org/docs/sw/m1n1-user-guide/
> - Tethered Boot Setup (For Developers) — AsahiLinux/docs 仓库 wiki

### 关键发现:**不用自己规划卷**

之前我以为要手搓一个 stub 卷。**实际上有现成流程,stub 由安装器自动创建。**

**① 先腾空间**(在 macOS 里)

```bash
diskutil list                    # 看清容器和分区号
diskutil apfs resizeContainer disk0s2 100GB
```

> ⚠️ **别把 macOS 缩到 70 GB 以下。** 需要 macOS 12.3+ 和管理员密码。
> 这一步只是缩小 macOS 容器、腾出未分配空间,不动数据。

**② 跑安装器**(它会创建约 3 GB 的 stub 容器,命名 "Linux")

```bash
curl -L https://mrcn.st/alxsh | sh
```

提示选 stub 的基础版本时,选 **macOS 12.1**。

**③ 进 1TR 跑 step2**

按电源键 → 选项 → 终端:

```bash
/Volumes/Linux/step2.sh
```

这一步"为自定义内核做好准备",并把 m1n1 设为那个 stub 的内核。

### 如果走手动方式

在 1TR 里:

```bash
kmutil configure-boot -c m1n1.bin \
    --raw --entry-point 2048 --lowest-virtual-address 0 \
    -v /Volumes/Linux
```

**`-v` 指向的就是那个 stub 容器**(名字叫 `Linux`),
**不是 `Macintosh HD`。**

### 已知的坑

| 报错 | 原因 |
|---|---|
| `not paired` | 不是从**目标卷自己的**恢复环境里跑的 |
| `Fileset Error: Invalid Mach-O boot properties` | 目标卷不是默认启动磁盘 |

> 🚨 **最要紧的一条**:`-v` 指向的**绝对不能是 macOS 那个卷**。
> 指错了可能让 macOS 起不来 —— 那正是备份要救的场面。

### ✅ 关于依赖 Asahi 安装器 —— 已明确,无异议

**用他们的安装器和 `step2.sh` 是可以的。**

项目定位已经写死([../README.md](../README.md)):

> **能用,但不合并。** 依赖、工具、安装器、公开代码随便用;
> 只是**产出的东西绝不回到那边去**。

所以这里直接用现成流程,不用自己复刻 stub 容器的创建。

---

## ⑥ 重启,选 m1n1

重启 → 按住电源键 → 启动选项里应多出一个入口 → 选它。

- 起来了 → 走 ⑦
- 黑屏重启 → 记下现象,回 ⑤ 检查装错没
- 启动项没出现 → `kmutil` 没写成功,回 ⑤

---

## ⑦ 建连接 —— **判据在这里**

> 同样来自公开文档摘要,**对照原文核对**。

### 宿主侧依赖(在游戏本上)

```bash
pip3 install --user pyserial construct serial.tool
```

> ⚠️ Ubuntu 24.04 起 `pip3 install --user` 会被 PEP 668 拦。
> 用 venv,或者加 `--break-system-packages`。

### 调试口在哪个口

**MacBook:左侧最靠屏幕的那个雷雳口。**
(不是随便一个口 —— m1n1 的 device-mode USB 走的是特定的那个。)

### 连上去

```bash
export M1N1DEVICE=/dev/ttyACM0
```

**看到 m1n1 的交互提示符 = M1 完成。** 🎉

> 认不到 `/dev/ttyACM0`?
> 1. 先确认插的是**那个口**
> 2. 再确认线是数据线(§1.4)
> 3. 最后怀疑 m1n1 没真起来 —— 回 ⑥ 看

### 之后怎么引导内核(M6 会用到)

```bash
python3 proxyclient/tools/linux.py -b 'earlycon debug rootwait' Image.gz <dtb>
```

**参数顺序:内核在前,dtb 在后**,initramfs 可选放最后。

---

## 失败了怎么办

**别慌,也别乱试。** 按这个顺序:

1. **M5 能不能正常进 macOS?** 能 → 问题只在 m1n1 那侧,数据没事
2. **进不去 macOS?** → 进恢复环境,或走 DFU(M3 MBA + Apple Configurator)
3. **实在不行** → 把现象、串口输出、报错原文贴给我

**只要备份在、M3 MBA 在,就没有救不回来的情况。**

---

## 这一步的产出

完成后:

- M5 能进 m1n1
- 下一步是 **M2:dump 原始 ADT**

**到时候告诉我 M1 的结果** —— 成功就把 m1n1 的版本号记进 [PROVENANCE](PROVENANCE.md),
失败就把报错贴上来。
