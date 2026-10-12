# 装了 m1n1 之后怎么回 macOS?

## ⚠️ 动手前:先把当前策略备份下来(3 分钟,出事时能救命)

改任何 boot policy 之前先存一份"现在的样子" —— 出问题才有对照物。

```bash
VGID=$(diskutil apfs listVolumeGroups | grep -B4 'Macintosh HD' | grep -oE '[0-9A-F-]{36}' | head -1)
OUT=~/boot-policy-backup-$(date +%F).txt
{ sudo bputil -d -v "$VGID"; echo; sudo csrutil status; echo; nvram boot-args 2>&1; } > "$OUT"
```

> 🚨 **这份文件里有你机器的唯一标识(ECID 等)。不要传公开仓库,不要贴进聊天。**

**改完之后再采一次,逐字对比。** 对照时看这些字段(值因机器而异,这里只列字段名和"正常的 macOS 应该是什么"):

| 字段 | 含义 | macOS 正常值 |
|---|---|---|
| `OS Type` | 当前环境类型 | `macOS` |
| `OS Pairing Status` | 与 recoveryOS 的配对状态 | `Not Paired` |
| `Security Mode (CSEC)` | 安全模式 | `1` |
| `Local Boot (lobo)` | 允许本地启动 | `1` |
| `Pairing Integrity` | 策略完整性 | `Valid` |
| SIP(`csrutil status`) | | `enabled` |

**逐字一致 = 没动到 macOS。**

---

## ⭐ 答案(2026-10-11 查实):`csrutil enable`

来源:`ImAtomiskk/asahim5` 的 `notes/uninstallation.md`,**同一台机器(J704)实测过**。

```
1. 关机(长按电源 10 秒)
2. 按住电源键 → 「正在载入启动选项」→ 松开
3. 选「选项」→ Continue            ← 进恢复环境(1TR)
4. 工具 → 终端
5. csrutil enable                  ← 重置启动策略
6. 输密码 → 重启
```

> ⚠️ **提示时不要选"启用完整安全"** —— m1n1 文档明说那会**把 m1n1 卸掉**。

**`csrutil enable` 之后,这个卷就恢复正常启动 macOS 了。**

### 切换的代价

| | |
|---|---|
| 装 | 1TR 里一条 `kmutil` 命令 |
| 用 m1n1 | 重启即进(它等 USB 连接) |
| **回 macOS** | **进一次 1TR,敲 `csrutil enable`** |

**不是一键切换** —— 每次都要过一趟恢复环境。

### 🚨 进了恢复环境之后,只敲这一条,别的都别碰

同一台机器上有人在恢复环境里**顺手开了磁盘工具、点了 Erase**,
结果**整盘被抹**(含固件和恢复环境),恢复花了 6 小时。
他自己推测诱因就是"**装过 m1n1 之后系统状态被改过**"。

**尤其:别开磁盘工具。**

---

## 另一条路:独立 stub 卷(官方)

- **用独立 stub 卷 → 根本不需要"回"**,macOS 从来没被动过
- 但**官方安装器拒绝 M5**(`j704ap` 不在 `DEVICES` 表里),而手工建 stub
  需要从 IPSW 还原一个最小 macOS —— 等于重写安装器

---

## 两条路的区别

| | ❌ 写 macOS 那卷 | ✅ 独立 stub |
|---|---|---|
| `kmutil -v` 指向 | `/Volumes/Macintosh HD - Data` | `/Volumes/Linux` |
| macOS 的 LocalPolicy | **被改** | **没动** |
| 之后能启动 macOS 吗 | **不能**(启动器里选它 = 跑 m1n1) | **能**(那是另一个启动项) |
| 需要腾空间 | 不用 | 要(≥80 GB) |

> ImAtomiskk 的路子:重启后**不再出现苹果 logo,而是 asahi logo** ——
> 因为在启动器里选 "Macintosh HD" 也是跑 m1n1。
>
> **他整个 `recovery.md` 的存在,就是这个后果。**

---

## 官方方案(推荐)

来源:`AsahiLinux/docs` 的 `docs/platform/dev-quickstart.md`(标注 obsolete,但流程清楚)
与现代的 `curl https://alx.sh | sh` 安装器(expert mode 有 tethered-only proxy 选项)。

### 现代做法

```bash
curl https://alx.sh | sh
```

选 expert mode → **只装 m1n1 的 tethered-only proxy 模式**。
安装器负责建 stub 卷、铺好一切。

### 手工做法(想理解原理)

**在 macOS 里:**

```bash
diskutil apfs resizeContainer disk0s2 <留给 macOS 的 GB>
diskutil addPartition disk0s2 APFS Linux 80GB      # 卷名必须叫 Linux
```

> ⚠️ 每次 `addPartition` 要传**前一个**分区的节点名,而它可能变 ——
> **每次之前先 `diskutil list`**,拿最后一个分区的设备名。重启后会重置。

**进 1TR:**

```bash
diskutil apfs listVolumeGroups | grep -B3 Linux | grep Group
bputil -nkcas        # 选那个 Linux 的 OS install ID
csrutil disable
```

> 报 `Failed to create local policy` 之类的权限错 → 先 `csrutil clear`。

**然后 kmutil 指向那个 stub:**

```bash
kmutil configure-boot -c ".../m1n1.bin" --raw \
    --entry-point 2048 --lowest-virtual-address 0 \
    -v /Volumes/Linux
```

---

## 真要撤销怎么办

因为 macOS 没被动过,所以:

1. **启动选择器里选 macOS** —— 正常回去
2. 不想要那个 stub 了 → 进 1TR,把 Linux 容器删掉,再把 macOS 容器扩回去
   (`diskutil apfs deleteContainer` + `diskutil apfs resizeContainer disk0s2 0`)

> ⚠️ **别用磁盘工具的 GUI 删。** 官方文档在 `deleting-an-install.md` 开头就写着
> **"Do not use Diskutil GUI"** —— 而且同一台机器上有人用 GUI 的 Erase
> **误抹了整盘**,恢复花了 6 小时。

---

## 🚨 唯一能真把机器搞坏的东西:**NOR Flash**

`dev-quickstart.md` 原文:

> **M1 Mac 实际上几乎不会变砖 —— 只要你不写 SPI Flash。**
> 我们**强烈不建议在 Linux 设备树里声明 NOR Flash**:
> 那上面存着 **vital product identification 和校准数据**,
> 搞坏了**只能送回 Apple**。没有任何理由去碰它。

**行动项:写设备树时,不要声明 NOR flash / SPI flash 节点。**
