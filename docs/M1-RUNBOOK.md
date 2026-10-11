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

> ## ⚠️ 动 `kmutil` 之前,先读 [HOW-TO-UNDO.md](HOW-TO-UNDO.md)
>
> **`-v` 指向哪个卷,决定了之后能不能回 macOS:**
>
> | 指向 | 后果 |
> |---|---|
> | ✅ **独立 stub 卷**(`/Volumes/Linux`) | macOS 的 LocalPolicy 没动 → 启动器里选 macOS 就回去 |
> | ❌ **macOS 自己的卷** | **启动被顶掉,回不去** —— 启动器里选 "Macintosh HD" 也是跑 m1n1 |
>
> **推荐官方方案**(安装器 / 独立 stub)。
> 下面 §⑤b 那套是**写 macOS 卷**的 —— 在同一台机器上实测过,
> 但**有上面那个代价**。

---

## ⑤b ImAtomiskk 的实测步骤(⚠️ 写的是 macOS 卷)

> 来源:`ImAtomiskk/asahim5` 的 `notes/installation.md`(**同一台机器 J704** 实测)。
> 我原来那套(stub 卷 / 跑 Asahi 安装器)**作废**。

### ① 先把整个 m1n1 文件夹拷到 U 盘

recoveryOS 里读不到你 Mac 上的文件,所以要走 U 盘:

```
/Volumes/<U盘>/
└── m1n1/
    └── build/
        ├── m1n1.macho
        ├── m1n1.bin
        └── ...
```

(整个文件夹都要 —— 后面 proxyclient 的脚本还要用)

### ② 进 1TR 后,先确认**真的**在 1TR

> **看菜单栏「工具」菜单里有没有「恢复助理」。**
> **没有 → 退出重启,重进。** 没有它 `kmutil` 会静默失败或报权限错。

### ③ 挂载 U 盘

```bash
diskutil list                 # 找到 U 盘,记下 /dev/diskXsY
diskutil mount /dev/diskXsY
ls /Volumes/                  # 确认它出现在这里
```

### ④ 写入

```bash
kmutil configure-boot \
  -c "/Volumes/<U盘>/m1n1/build/m1n1.bin" \
  --raw \
  --entry-point 2048 \
  --lowest-virtual-address 0 \
  -v "/Volumes/Macintosh HD - Data"
```

> ⚠️ **注意 `-v`**:他们实测**直接指向 macOS 数据卷**(`/Volumes/Macintosh HD - Data`),
> **不建 stub 卷**。这和我之前推断的完全不同。
> **先 `diskutil list` 确认你那台的数据卷叫什么** —— 名字可能不一样。
>
> **成功的话没有任何输出。** 报权限错 = 你不在 1TR,回 ②。

### ⑤ 重启

```bash
reboot
```

屏幕会显示 asahi logo → 变黑 → 出一些日志。**这是正常的,m1n1 在跑。**

---

## ⑥ 重启,选 m1n1

重启 → 按住电源键 → 启动选项里应多出一个入口 → 选它。

- 起来了 → 走 ⑦
- 黑屏重启 → 记下现象,回 ⑤ 检查装错没
- 启动项没出现 → `kmutil` 没写成功,回 ⑤

---

## ⑦ 建连接 —— **判据在这里**

### 宿主侧(游戏本上)

```bash
cd m1n1
pip3 install -r proxyclient/requirements.txt
export M1N1_PORT=/dev/ttyACM0
python3 proxyclient/tools/shell.py
```

> ⚠️ 是 **`M1N1_PORT`**,不是 `M1N1DEVICE`(我前面写错了)。
>
> 权限被拒的话:
> ```bash
> sudo usermod -aG dialout $USER    # 然后注销重登
> ```

### 判据

**Python 提示符出现 = M1 完成。** 🎉

```python
>>> p.chip_id()      # 应返回 T8142
>>> p.read32(0x...)
```

### ⚠️ 已知问题:读出来**全是 0**

**这不是你的问题,是已知的、别人也遇到的。**

> m1n1 的 proxy client 把 **M1/M2 时代的 MMIO 基址硬编码**在 `proxyclient/hw/` 里,
> M5 上这些地址挪了。客户端读错地方,静默返回 0。

**能连上就是成功。** 修基址是下一步。

---

## ⑦b ⭐ 连上之后的下一步 —— **别人卡在这,你从这开始**

**别急着 dump 设备树。第一件事是抓 m1n1 的启动日志:**

```bash
picocom -b 115200 /dev/ttyACM0 | tee m5_boot_log.txt
```

> **m1n1 启动时会打印真实的地址表** —— 不经过那个坏掉的 proxy。
> **这份日志是所有后续工作的地基。** 存好。

然后按顺序:

1. 把日志里的地址和 `proxyclient/hw/` 里的硬编码对比
2. **锚定 UART**(它本来就活着)—— 先让 `p.read32` 返回非零
3. 看偏移是不是**统一的** —— 统一的话改一处就够,不统一就得逐个来

### m1n1 **自带**我们要的工具 —— 别再自己写

| m1n1 自带 | 作用 | 我们之前打算自己写的 |
|---|---|---|
| `proxyclient/adt.py` | **dump / diff Apple 设备树** | ← M2 的目标 |
| `proxyclient/tools/pmgr_adt2dt.py` | **ADT → 设备树转换** | ← 我们的 `adt2dts.py` |
| `proxyclient/tools/shell.py` | proxy shell | |
| `proxyclient/tools/run_guest.py` | hypervisor 模式 | |
| **`proxyclient/hw/`** | **硬编码 MMIO 基址 —— M5 要修的就是这里** | |

> **不要再造轮子。** `pmgr_adt2dt.py` 就是"ADT→DTS",我们的工具只需要做**补充**
> (比如它在 ioreg 数据上的用法),不需要重写转换器本身。

---

> ## 🚨 做完这一步之后:别在恢复环境里用磁盘工具的 Erase
>
> 同一台机器上有人**误抹了整个盘(含固件和恢复环境)**,推测诱因就是
> "之前的折腾改动了系统状态"让 Disk Utility 没认出启动卷。
> **恢复花了 6 小时。** 详见 [RISKS.md](RISKS.md)。

## 失败了怎么办

**别慌,也别乱试。** 按这个顺序:

1. **M5 能不能正常进 macOS?** 能 → 问题只在 m1n1 那侧,数据没事
2. **进不去 macOS?** → 进恢复环境,或走 DFU
3. **实在不行** → 把现象、串口输出、报错原文贴给我

**DFU 恢复不一定需要 Mac 了** —— 他们实测 **Ubuntu 也能做**:

```bash
sudo apt install libimobiledevice idevicerestore
sudo idevicerestore -e <你的 IPSW>     # IPSW 从 ipsw.me 下载
```

> ⚠️ **但要先备好 IPSW。** 建议现在就下好一个 macOS IPSW 存着。
> 而且注意:`recovery.md` 里写着,如果走到「圆圈叹号」那一步、
> **又没有 IPSW 可刷,数据就全没了。**

**DFU 进入方式**(必须先关 MagSafe,只用 USB-C 连):
按住电源 10 秒关机 → 按一下电源 → 立刻同时按住 **左Ctrl + 左Option + 右Shift + 电源**,
约 10 秒后松开除电源外的键 → 继续按电源最多 10 秒,直到主机上出现 DFU 窗口。

---

## 这一步的产出

完成后:

- M5 能进 m1n1
- 下一步是 **M2:dump 原始 ADT**

**到时候告诉我 M1 的结果** —— 成功就把 m1n1 的版本号记进 [PROVENANCE](PROVENANCE.md),
失败就把报错贴上来。
