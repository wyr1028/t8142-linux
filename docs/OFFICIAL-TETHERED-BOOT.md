# 官方 Tethered Boot 文档要点

来源:`AsahiLinux/docs` 仓库 `docs/sw/tethered-boot.md` 与 `docs/hw/soc/serial-debug.md`
(2026-10-11 拉取)。**这是权威版本**,比第三方笔记可信。

---

## 1 ⚠️ 我们之前搞错了:安装方式

官方给的是**用官方安装器**,不是手工 `kmutil`。

```bash
curl https://alx.sh | sh
```

> 安装器有 **expert mode**,可以选 **"只装 m1n1 的 tethered-only proxy 模式"** ——
> **这正是我们要的。**

### m1n1 分两阶段

| 阶段 | 位置 | 说明 |
|---|---|---|
| **stage 1** | 1TR 安装时装上去 | **装完就不能改**(除非再进恢复) |
| **stage 2** | EFI 分区 `m1n1/boot.bin` | 发行版可以更新它来加硬件支持 |

**release 版的 stage 1 带"后门 proxy 模式"**,要从 1TR 打开。

### 打开 proxy 模式

```bash
csrutil disable && nvram boot-args=-v
```

然后**选 Asahi Linux 卷并认证**。

> 原理:用 SIP 的 disable 标志(施加在 Asahi 卷上)告诉 m1n1 开后门;
> `boot-args=-v` 也参与判断。**这个改动是按卷的,不影响 macOS。**
>
> ⚠️ **配对错误** = 默认启动卷和你改的卷不是同一个(只能给默认启动卷降安全设置)。

### 之后的行为

m1n1 启动时会**等 5 秒**。如果检测到 USB 连接、且主机打开了对应的 TTY 设备,
就**中断正常启动、进入 proxy 模式**;否则正常启动。

**所以机器平时还能单独用,需要 tethered 时插上就行。**

---

## 2 ⭐ 三条我们完全不知道的

### 2.1 `picocom-sec.sh` —— 进 proxy 的正确姿势

```bash
proxyclient/tools/picocom-sec.sh
```

它会**等 m1n1 设备接入,然后打开它的第二个 USB 设备当串口**。

**这一条同时干两件事**:① 打断 m1n1 让它进 proxy 模式 ② 提供虚拟串口控制台。

> 我们之前只知道的 `shell.py` 是进 Python shell 的;**进 proxy 模式本身要靠这个脚本。**

### 2.2 proxy ABI 不稳定 ⇒ **两边的 m1n1 必须同版本**

> "Chainload a plain m1n1 binary first, to ensure the target machine is running
> a version that matches the m1n1 tree/tools in the host (**since the proxy ABI
> is not stable**)"

所以:主机上的 m1n1 树和 M5 上跑的 m1n1 **版本要对齐**,否则协议对不上。

### 2.3 udev 规则

装 m1n1 仓库里的 `udev/80-m1n1.rules` 到 `/etc/udev/rules.d`,
不然设备名很难看、权限也可能不够(可能要加 `uucp` 组)。

---

## 3 宿主侧依赖(官方原文)

```bash
pip3 install --user pyserial construct serial.tool
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1 && make          # 原生 aarch64 用 make ARCH=
```

外加 `picocom`。

---

## 4 连接

- 用 **USB Type-C 线**(C-C 或 **C-A 都行**,A 端在主机)
- **必须插 target 的雷雳口** —— 对 MacBook 是**后左那个口**(靠屏幕)
- 建议再给 target 的另一个口接电源

---

## 5 启动内核

### 直接启动(不用 hypervisor)

```bash
python3 proxyclient/tools/linux.py -b 'earlycon debug rootwait root=/dev/nvme0n1p5 <其它>' \
        /path/to/Image.gz /path/to/<board>.dtb [可选 initramfs]
```

**顺序:内核 → dtb →(可选)initramfs。** 内核要 **gzip** 过。

### 在 hypervisor 下启动(推荐,崩溃不会死机)

```bash
tools/run_guest_kernel.sh /path/to/linux/build/dir 'earlycon rootwait root=...' [initramfs]
```

它会在 guest 里跑内核,可以用 `^C` 打断、`bt` 打栈回溯、`cpu(1)` 切核、`gdbserver` 接调试器。

> ⚠️ initramfs **要先合并再 gzip**(不是先 gzip 再合并)。

---

## 6 物理串口 —— **我们不需要**

`serial-debug.md` 说:M1 Mac 的调试串口复用在 **DFU 那个 Type-C 口**上,
是 **1.2V 电平的 UART**,要靠**厂商私有的 USB-PD VDM 命令**打开,
所以线必须是 **USB 3 / SuperSpeed**(>15 根线),充电线不行。

配套工具:`macvdmtool`(仅 macOS/M1 时代),还能用 VDM 命令**硬重启目标机**。

> **但 tethered-boot.md 明确写了:这不是必需的。**
> "most developers will find the **virtual serial port offered by the m1n1 hypervisor**
> to be adequate for everything"。
>
> **所以我们不用买/做那根特殊线。**

---

## 7 对 ImAtomiskk 那条路的评价

他的 `installation.md` 用的是**手工 `kmutil configure-boot -v "/Volumes/Macintosh HD - Data"`**
—— 那是**另一条路**,不是官方流程。

| | 官方(安装器) | ImAtomiskk(手工 kmutil) |
|---|---|---|
| 建 stub 卷 | ✅ 安装器建 | ❌ 直接写到 macOS 数据卷 |
| macOS 还能正常启动吗 | ✅ 能(按卷隔离) | ⚠️ 不确定 |
| 打开 proxy 模式 | `csrutil disable && nvram boot-args=-v` | 不需要(直接以 m1n1 为启动对象) |
| 官方支持 | ✅ | ❌ |

**建议走官方那条。** 但他那条也实测过,可以作为备用。

---

## 8 环境要求

- target:Apple Silicon Mac,**macOS ≥ 12.3**,有**密码保护的管理员账号**
- host:任意架构的 GNU/Linux(macOS 也支持但"less well tested")
- Python ≥ 3.9
