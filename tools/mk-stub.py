#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# 手工驱动 asahi-installer 的 StubInstaller，在一个独立容器里建 stub（macOS 的
# "假系统"），好让 1TR 认出一个可启动项给 m1n1 挂靠。
#
# 设计要点：绕开 main.py 的交互向导，直接调库，目标分区硬编码 + 前置断言 ——
# 保证所有写操作只落在指定容器里，绝不碰 macOS。
#
# 完整背景、macOS 27 的三处适配、当前卡点，见 docs/STUB-INSTALL.md。
#
# 用法（需要 root）：
#   sudo python3 tools/mk-stub.py
#
# 依赖的前置补丁（见 docs/STUB-INSTALL.md「三个 macOS 27 适配点」）：
#   1. src/stub.py 里 bless2["RestoreBundlePath"] → .get(..., "restore")
#   2. src/stub.py 里 OTA 分支的 arm64eBaseSystem.dmg 改从本机 Recovery 卷拷

import sys, os, subprocess

# ── 可调参数 ────────────────────────────────────────────────────
# 原料默认放在仓库的 upstream/ 下（该目录被 .gitignore 忽略，见 docs/STUB-INSTALL.md）：
#   upstream/asahi-installer/                     ← 安装器源码
#   upstream/Install macOS 27 Golden Gate.app/    ← OTA 资产来源
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

SRC_REPO   = os.path.join(_ROOT, "upstream", "asahi-installer")
DMG        = os.path.join(_ROOT, "upstream", "Install macOS 27 Golden Gate.app",
                          "Contents/SharedSupport/SharedSupport.dmg")
TARGET_PART = "disk0s5"      # stub 容器所在物理分区（diskutil list 里核对）
TARGET_CTR  = "disk4"        # 该分区对应的 APFS 容器（重启后编号会变，务必核对）
LABEL       = "Linux"        # 目标卷名（stub.py 用它派生 "Linux - Data" 等）
MACOS_VER   = "27.0.1"       # 与 OTA 包一致
# ────────────────────────────────────────────────────────────────

SRC = os.path.join(SRC_REPO, "src")   # SRC_REPO 已是绝对路径，sudo 下也成立
if not os.path.isdir(SRC):
    sys.exit(f"找不到 {SRC} —— 原料要放在仓库的 upstream/ 下，见 docs/STUB-INSTALL.md")
sys.path.insert(0, SRC)
os.chdir(SRC)                      # stub.py 用相对路径读 logo.icns / step2/


def die(msg):
    print(f"\n!! 中止: {msg}")
    sys.exit(1)


def main():
    import system, diskutil, osenum, stub

    # ── 1. 挂载 OTA 包 ────────────────────────────────────────
    mount = "/Volumes/Shared Support"
    if not os.path.isdir(mount):
        print("[*] 挂载 SharedSupport.dmg ...")
        subprocess.run(["hdiutil", "attach", DMG, "-nobrowse", "-quiet"], check=True)

    zip_path = None
    for root, _dirs, files in os.walk(mount):
        for f in files:
            p = os.path.join(root, f)
            if f.endswith(".zip") and os.path.getsize(p) > 1e10:
                zip_path = p
    if not zip_path:
        die(f"在 {mount} 下找不到 OTA zip")
    print(f"[+] OTA 包: {os.path.basename(zip_path)}")

    # ── 2. 环境对象 ───────────────────────────────────────────
    si = system.SystemInfo()
    print(f"[*] chip_id=0x{si.chip_id:04X} board_id=0x{si.board_id:02X} "
          f"device_class={si.device_class} macos_ver={si.macos_ver}")

    d = diskutil.DiskUtil()
    d.get_info()

    # ── 3. 目标卷 + 断言（全部写操作唯一入口）─────────────────
    part = d.get_partition_info(TARGET_PART)
    if part.container is None:
        die(f"{TARGET_PART} 没有关联容器")
    ctr = part.container["ContainerReference"]
    if ctr != TARGET_CTR:
        die(f"{TARGET_PART} 指向 {ctr}，期望 {TARGET_CTR}")
    if part.label != LABEL:
        die(f"{TARGET_PART} 卷名是 {part.label!r}，期望 {LABEL!r}")
    for v in part.container["Volumes"]:
        if v["DeviceIdentifier"].startswith("disk3") and "Macintosh" in v.get("Name", ""):
            die(f"容器里混进了 macOS 卷 {v['DeviceIdentifier']}")
    print(f"[+] 断言通过: {TARGET_PART} → {ctr}，"
          f"容器内卷 = {[v['DeviceIdentifier'] for v in part.container['Volumes']]}")

    # ── 4. 找当前 macOS 作为 cur_os（install_files 要复制 admin 用户）──
    sysdsk = d.find_system_disk()
    parts = d.get_partitions(sysdsk)
    oe = osenum.OSEnum(si, d, sysdsk)
    oe.collect(parts)                       # 纯只读
    cur_os = None
    for p in parts:
        for o in (p.os or []):
            if o.vgid == si.boot_vgid and not o.stub:
                cur_os = o
    if cur_os is None:
        die(f"找不到当前启动的 OS (boot_vgid={si.boot_vgid})")
    print(f"[+] cur_os = {cur_os.label}")

    # ── 5. 假 IPSW 对象（stub.py 只取 .version / .url）──────────
    class OTA:
        version = MACOS_VER
        url = zip_path

    # ── 6. 三步 ───────────────────────────────────────────────
    ins = stub.StubInstaller(si, d, oe)
    ins.load_ipsw(OTA)
    ins.prepare_volume(part)
    ins.check_volume()
    print(f"[+] stub 就绪: vgid={ins.osi.vgid}")
    print(f"    system={ins.osi.system} data={ins.osi.data}")
    print(f"    preboot={ins.osi.preboot} recovery={ins.osi.recovery}")

    ins.install_files(cur_os)

    print("\n[+] stub 安装完成")
    print(f"    boot.bin 待补: {ins.boot_obj_path}")
    print(f"    （把 m1n1.bin 拷到那里，见 docs/STUB-INSTALL.md）")


if __name__ == "__main__":
    main()
