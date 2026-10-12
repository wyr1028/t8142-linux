# 手工建 stub 装 m1n1（Asahi 安装器的 tethered-only 路线）

> **目标**：给 m1n1 一个**独立启动项**，且**完全不碰 macOS**。
> **状态（2026-10-11）**：stub 已建成、1TR 能看见、能进去，**卡在 `bless`**（见 [卡在哪](#卡在哪)）。
> **产物**：`tools/mk-stub.py`（驱动脚本）、两处 `stub.py` 补丁（见 [适配点](#三个-macos-27-适配点)）。

---

## 为什么走这条而不是「写 macOS 卷」

| | ❌ 写 macOS 卷（`kmutil -v /Volumes/<macOS Data>`） | ✅ 独立 stub 卷（本文） |
|---|---|---|
| macOS 的 LocalPolicy | **被改** | **没动** |
| 启动器里选 "Macintosh HD" | **也跑 m1n1**，回不去 | 正常回 macOS |
| 要不要手敲命令 | 要（1TR 里敲 `kmutil`） | 不要 —— 全自动，只有一次密码输入 |
| 同机实测 | ✅ `ImAtomiskk/asahim5` 走通过 | ❌ 无先例（本文是第一份记录） |
| 出处 | `docs/M1-RUNBOOK.md` §⑤b | 本文 |

代价：多占一个容器（80 GB）+ 走通之前需要折腾 bless。

---

## 三个 macOS 27 适配点

Asahi 的 `stub.py` 是按 **macOS ≤14** 的启动栈写的。在 27 上有三处必须改，
**这是「stub 路线在 M5 上没先例」的真实原因** —— 不是没人试，是要跟的版本变了。

### ① `bless2.RestoreBundlePath` 被删

`AssetData/boot/usr/standalone/bootcaches.plist` 里的 `bless2` 字典：

| | 旧（≤14） | macOS 27 |
|---|---|---|
| 键 | `RestoreBundlePath` 等 | `Version` / `SupportsPairedRecovery` / `SupportsExternalPrebootObjects` / `ExtraPaths` / `BootObjects` |
| 机制 | Preboot 里塞一个 Restore bundle | 换成 `usr/standalone/firmware/*.img4` 一堆固件 |

**改法**（`src/stub.py`，共 3 处）：

```python
# 原： bless2["RestoreBundlePath"]
# 改： bless2.get("RestoreBundlePath", "restore")
```

路径 `restore/` 依然存在，只是键名没了 —— 本机 macOS 的
`Preboot/<vgid>/restore/` 就是活证据。

### ② `pbzm` 取代 `pbzx`（压缩容器换代）

OTA 包里 `AssetData/payloadv2/basesystem_patches/arm64eBaseSystem.dmg` 是个
`BXDIFF50` 容器，内层压缩流的 magic 从 `pbzx` 变成了 **`pbzm`**：

```
+60: 70 62 7a 6d   "pbzm"
+64: 00 00 00 00 00 10 00 00   大端 = 1 MiB   (blocksize)
+72: 00 00 00 00 00 10 00 00   大端 = 1 MiB   (chunk 未压缩大小)
+80: 00 00 00 00 00 00 29 e0   大端 = 10,720  (压缩后大小)
```

Apple 的 `pbz*` 是「`pbz` + 算法字母」家族（已知 `x`=xz、`e`=LZFSE、`4`=LZ4、
`z`=zlib、`b`=LZBITMAP）。**`m` 不在已知列表里**，且块内数据不是
xz/lzma/zlib/gzip 任何一种（实测全失败）。**未公开，Python 侧解不了。**

**绕法（本文采用）**：**不解析它**。系统启动时已经把**逐字节相同**的文件解好放在本机
Recovery 卷里了：

```
/Volumes/Recovery/<macOS vgid>/usr/standalone/firmware/arm64eBaseSystem.dmg
  → 1,827,862,528 字节，与 BXDIFF50 头里声明的 size 完全一致
```

```python
# src/stub.py：OTA 分支改为从本机 Recovery 直接拷
_src = os.path.join("/Volumes/Recovery", self.sysinfo.boot_vgid,
                    "usr/standalone/firmware/arm64eBaseSystem.dmg")
shutil.copy(_src, os.path.join(basesystem_path, "arm64eBaseSystem.dmg"))
```

### ③ 设备检查其实不是问题

传说「安装器拒绝 M5」。实测：`load_identity()` 要的五项在**本机 OTA 包**里全中 ——

| 条件 | 值 |
|---|---|
| `ApBoardID` | `0x22` |
| `ApChipID` | `0x8142` |
| `DeviceClass` | `j704ap` |
| `RestoreBehavior` | `Update` |
| `Variant` | `macOS Customer Software Update` |

它拦的是「从 Asahi 服务器按设备拉 macOS」那一步。**喂本机包就绕过了。**

---

## 怎么做

### 原料

**统一放在仓库的 `upstream/` 下**（该目录被 `.gitignore` 忽略，体积大、按需重新获取）：

```
upstream/
├── Install macOS 27 Golden Gate.app/     ← OTA 资产来源（17 GB）
├── asahi-installer/                      ← 安装器源码
└── m1n1/                                 ← m1n1 源码 + build/
```

| 需要 | 从哪来 | 放哪 |
|---|---|---|
| macOS 27 的 OTA 资产 | `Install macOS 27.app` 里的 `Contents/SharedSupport/SharedSupport.dmg`（其中那个 17 GB zip 就是 OTA 包） | `upstream/` |
| Asahi 安装器源码 | `git clone https://gh-proxy.com/https://github.com/AsahiLinux/asahi-installer.git`（**只读用，不回馈**） | `upstream/asahi-installer/` |
| m1n1 | 见 `docs/M1-RUNBOOK.md` §① | `upstream/m1n1/` |

`tools/mk-stub.py` 按**脚本相对位置**推导这三个路径，所以换机器只要照上表摆好就行，不用改代码。

### 编译 m1n1 的坑（M5/macOS 27 实测）

`M1-RUNBOOK.md` 说 `brew install make python3 gcc-aarch64-embedded`，**实测不需要那几个**：

- Makefile 走 `USE_CLANG=1` 分支 → 要的是 **clang + `ld.lld` + `llvm-objcopy`**
- 本机已有 `llvm@21` / `lld@21`（Cellar 里），**不必装新的**：

```bash
make -j"$(sysctl -n hw.ncpu)" \
  LLVMCONFIG=/opt/homebrew/Cellar/llvm@21/21.1.8/bin/llvm-config \
  LLDDIR=/opt/homebrew/Cellar/lld@21/21.1.8_1/bin/
```

- **Rust 那一环**：需要 `rustup default stable` + `rustup target add aarch64-unknown-none-softfloat`。
  本机原来的 `stable-aarch64-apple-darwin` 是**损坏的**（`missing manifest`），得重装。
  当前 commit 的 workaround 正好针对 `rustc 1.99.0`，版本要对上。
- 判据：`build/` 下同时出现 `m1n1.bin`（3.7M）和 `m1n1.macho`（1.1M）。

### 建 stub

```bash
sudo python3 tools/mk-stub.py     # 见该脚本；目标卷硬编码为 Linux 容器，带前置断言
```

脚本做的三件事（对应 `stub.py` 的 `load_ipsw` / `prepare_volume` / `install_files`）：

1. `load_ipsw` —— 喂本机 OTA zip（`url` 不以 `.ipsw` 结尾即走 OTA 分支）
2. `prepare_volume` —— 在目标容器建 **Data → System(groupWith Data) → Preboot → Recovery**
3. `install_files` —— 铺 macOS 启动文件 + `.IAPhysicalMedia` + `Finish Installation.app`
4. 收尾：把 `m1n1.bin` 拷成 `Finish Installation.app/Contents/Resources/boot.bin`

### 自动化收尾（免手敲）

`step2.sh` 是被 `Finish Installation.app` **自动调起**的（靠 `.IAPhysicalMedia` 标记），
所以「在 1TR 里敲 `bputil`」这件事可以写进脚本 —— 见 `tools/`，或直接改
`/Volumes/Linux/Finish Installation.app/Contents/Resources/step2.sh`
（注意：System 卷默认**只读挂载**，改之前要 `mount -u -w /Volumes/Linux`）。

---

## 卡在哪

`bless --setBoot --device /dev/<stub System> --user <u> --stdinpass`
—— 即 `main.py:bless()` 那条 —— 失败：

```
Bootability failed Error Domain=BYErrorDomain Code=101 "Failed to mount volume"
  mount_apfs returned : 66

BootabilityService: Failed to mount source preboot:
  NSPOSIXErrorDomain Code=22 "Invalid argument"  mount_apfs returned : 66

Bootability summary: make bootable (target = <stub VGID>, bsd name = ...,
  security mode = full -> full, local policy = 0, install = 0, set boot = 0)
```

**`Failed to mount source preboot`，errno 66（EPERM）。** 挂载就被拒，后面都没开始做。

### 为什么这是死结

```
bless 失败  →  不成为默认启动卷  →  stub 的 recoveryOS 不是 1TR
                                        ↓
                              bputil 拒绝改策略
                                        ↓
                              没有 LocalPolicy  →  stub 永远起不来
```

### 两个环境的实测错误码（可复现）

| 在哪跑 `bputil` | 错误 | 含义 |
|---|---|---|
| macOS 的 1TR | `Code=17 "pairing (17)"` | 一个 recoveryOS 只能改**与它配对**的那个 OS（`bputil(1)` 手册） |
| stub 自己的 recoveryOS | `Code=11 "AP boot mode (11)"` | 该 recoveryOS **不在 1TR 模式**，无权改策略 |

**1TR 能改但改不着；stub 的 recoveryOS 改得着但不是 1TR。** 两头都不通。

### 未解的疑点（给接手的人）

1. **为什么挂载 Preboot 会 EPERM？** 卸载后再试、换 `--mount` 写法，都同样失败。
   （做过一次 `mount -u -w /Volumes/Linux`，但重启后复现，排除这个干扰。）
2. **`Preboot/<vgid>/` 里除了 `restore/`，还缺** `boot/`、`usr/standalone`、
   `PreLoginData/`、`cryptex1/`、`etc/`、`Library/` —— macOS 都有。
   `boot/` 按设计是 `kmutil configure-boot` 之后才生成的，但 bless 可能也依赖它。
3. **LocalPolicy 是个文件**：`Preboot/<vgid>/LocalPolicy/<nonce>.img4`
   （见系统日志 `com.apple.BootPolicy`）。SEP 签名，手搓不出来。

### 对 bless 的深入调查（2026-10-12，未成功，供接手者免于重复）

**结论：堵点在 Apple 私有框架内部，不在命令用法。** 以下是逐项试过的：

| 手段 | 做法 | 结果 |
|---|---|---|
| 挖二进制 | `strings /usr/sbin/bless`、`.../Bootability.framework/.../BootabilityService` | 见下 |
| Apple 调试开关 | `sudo launchctl setenv BYDisablePrebootBrain 1` 后重跑 | **无效** —— 开关设在 shell 环境，XPC 服务收不到 |
| 跟踪系统调用 | `fs_usage -f filesys` | 被 SIP 挡（空输出） |
| 换参数组合 | `--mount <CoreServices> --create-snapshot` | 暴露挂载目标 |
| 手工挂同一卷对照 | `mount_apfs /dev/<stub System> /tmp/t1` | `Operation already in progress`（卷已挂） |

**从字符串里读出来的关键事实：**

- `BootabilityService` 里有 `Unmounting source preboot (%@)` ⇒ 那段逻辑是
  **「挂载 source preboot → 配置 → 卸载」**，我们卡在第 1 步。
- 它还依赖 `BootabilityBrain.framework`，报错文案包括
  `Brain framework is missing from preboot` / `Global trust cache is missing from preboot`
  / `Preboot restore version is invalid`。
- `--mount ... --create-snapshot` 暴露了真实动作：
  ```
  mount_apfs: volume could not be mounted: Permission denied
  mount: /private/var/folders/.../T/bless.tDbE failed with 66
  ```
  ⇒ 它想把卷**重挂到临时目录**，而内核拒了。
- **对照实验说明这不是"卷有问题"**：手工挂 macOS 自己的 Preboot 同样报
  `Operation already in progress` —— 同一个卷、同样的挂法，**bless 拿到的是
  `Permission denied` 而不是这个**，说明它先试图**卸下正在使用的卷**，那一步被内核拒。

**为什么判定"不宜再挖"：** 再往下需要动 macOS 自己在用的卷；且
`BootabilityBrain` / `bootpolicy` 是闭源私有框架。**M5 + macOS 27 这个组合
没有任何成功记录**（Asahi 用户能过是因为他们机器上这条路本来就通）。

**参考**：`bputil(1)` 手册、[[M1-RUNBOOK]] §⑤b（同机实测的替代路线，`kmutil -v`
指向 macOS 数据卷 —— 代价是顶掉 macOS 启动项，但 `HOW-TO-UNDO.md` 有撤销步骤）。

---

## 怎么撤销

`stub` 只占 disk4（80 GB），macOS 毫发未动。

```bash
# 进 1TR 后：
diskutil apfs deleteContainer <stub 容器>
diskutil apfs resizeContainer disk0s2 0      # 空间还给 macOS
```

> ⚠️ **别用磁盘工具的 GUI 删** —— `HOW-TO-UNDO.md` 记着同机有人用 GUI 的 Erase
> **误抹整盘**，恢复花 6 小时。

**验证 macOS 无恙**：`bputil -d -v <macOS VGID>` 与改动前逐字一致
（`OS Type: macOS` / `Not Paired` / `CSEC: 1` / `lobo: 1`）。

---

## 出处

| 事实 | 来源 |
|---|---|
| `bless2` 键变化、`RestoreBundlePath` 缺失 | 本机 OTA 包 `bootcaches.plist` 实测 |
| `pbz*` 家族与算法字母表 | [go-macos-pkg / dpp/FORMATS.md](https://github.com/Dil4rd/dpp/blob/HEAD/pbxz/docs/FORMATS.md) |
| `pairing` 语义、`bputil` 限制 | [`bputil(1)`](https://keith.github.io/xcode-man-pages/bputil.1.html)、[asahi-installer#50](https://github.com/AsahiLinux/asahi-installer/issues/50) |
| `bless` 在普通 macOS 必失败、须进 recovery | [asahi-installer#328](https://github.com/AsahiLinux/asahi-installer/issues/328) |
| LocalPolicy 位置 | 本机 `com.apple.BootPolicy` 系统日志 |
| M5 identity 在本机包内 | `AssetData/boot/BuildManifest.plist` 实测 |
