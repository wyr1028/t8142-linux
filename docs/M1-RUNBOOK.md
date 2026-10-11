# M1 操作手册:点亮 m1n1

> **这一步会改 M5 的 boot policy。** 前面三样准备(备份已验证 / DFU 兜底就位 / 数据线验过)
> 就是为了这里。
>
> 不确定的地方标 ⚠️,**不猜**。带 ⚠️ 的步骤必须先去读权威文档。

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

## ① 编译 m1n1(在 Linux 主机上)

```bash
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1
```

> ⚠️ **拉下来之后,先读仓库根的 `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`。**
> 那个项目明令禁止 AI 参与。**本项目的立场是:只读、不改、不提交。**
> 你自己读它没问题;别把 AI 写的东西送回去。见 [../LEGAL.md](../LEGAL.md)。

```bash
make
ls -l build/m1n1.bin
```

**判据**:出现 `build/m1n1.bin`。

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

## ⑤ 装启动对象 —— ⚠️ **这里必须读权威文档**

**我要诚实说清楚**:卷怎么规划,我**没有可靠来源**,不猜。

你要去找的是这两个地方:

1. **m1n1 User Guide** —— https://asahilinux.org/docs/sw/m1n1-user-guide/
2. m1n1 源码里自带的 README

要找的答案:

- **装到哪个卷上?** 文档里的做法通常是用一个**独立的小 APFS 卷**当 stub,
  这样 macOS 自己的卷不动、数据安全
- **要不要把那个卷设成默认启动磁盘?**
- **`-v` 后面到底填什么路径?**

命令的**形态**长这样(macOS ≥ 12.1):

```bash
kmutil configure-boot -c m1n1.bin \
    --raw --entry-point 2048 --lowest-virtual-address 0 \
    -v <目标卷>
```

**已知的坑**:

| 报错 | 原因 |
|---|---|
| `not paired` | 不是从**目标 OS 自己的**恢复环境里跑的 |
| `Fileset Error: Invalid Mach-O boot properties` | 目标卷不是默认启动磁盘 |

> **最要紧的一条**:`-v` 指向的**绝对不能是 macOS 那个卷**(通常叫 Macintosh HD)。
> 指错了可能让 macOS 起不来 —— 那正是备份要救的场面。

---

## ⑥ 重启,选 m1n1

重启 → 按住电源键 → 启动选项里应多出一个入口 → 选它。

- 起来了 → 走 ⑦
- 黑屏重启 → 记下现象,回 ⑤ 检查装错没
- 启动项没出现 → `kmutil` 没写成功,回 ⑤

---

## ⑦ 建连接 —— **判据在这里**

在 Linux 主机上:

```bash
cd m1n1
# 具体入口看仓库 README 与 user guide
```

**看到 m1n1 的交互提示符 = M1 完成。** 🎉

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
