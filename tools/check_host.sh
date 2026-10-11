#!/usr/bin/env bash
# 检查 Linux 主机是否准备好跑 tethered boot。
#
# **在第二台机器(游戏本上的 Ubuntu)上跑,不要在 M5 上跑。**
#
#     bash tools/check_host.sh
#
# 退出码 0 = 全绿,可以进 PLAYBOOK 的 M1;非 0 = 还有缺项。
#
# 为什么要有这个脚本:装完系统到动 M5 的 boot policy 之间,有一堆
# "以为装好了其实没有"的东西(udev 规则、Rust target、libusb 开发头文件)。
# **先把主机验干净,再去碰目标机的启动策略** —— 这是最容易省下时间的顺序。

set -u

G='\033[32m'; R='\033[31m'; Y='\033[33m'; N='\033[0m'
ok=0; bad=0

chk() {  # chk <说明> <检测命令> <缺了怎么办>
    if eval "$2" >/dev/null 2>&1; then
        printf "  ${G}✓${N} %s\n" "$1"; ok=$((ok+1))
    else
        printf "  ${R}✗${N} %s\n     ${Y}→ %s${N}\n" "$1" "$3"; bad=$((bad+1))
    fi
}

echo
echo "═══ 环境 ═══"
printf "  主机架构 : %s\n" "$(uname -m)"
printf "  发行版   : %s\n" "$(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || echo '未知')"
printf "  内核     : %s\n" "$(uname -r)"

if [ "$(uname -m)" = "aarch64" ]; then
    echo "  ${Y}注意${N}:这台是 arm64。可以原生编译 m1n1,不一定需要交叉工具链。"
fi

echo
echo "═══ 交叉工具链(在 x86 主机上是必需的)═══"
chk "aarch64-linux-gnu-gcc" \
    "command -v aarch64-linux-gnu-gcc" \
    "sudo apt install gcc-aarch64-linux-gnu"
chk "aarch64-linux-gnu-ld" \
    "command -v aarch64-linux-gnu-ld" \
    "sudo apt install binutils-aarch64-linux-gnu"

echo
echo "═══ 基础工具 ═══"
chk "make"    "command -v make"    "sudo apt install make"
chk "git"     "command -v git"     "sudo apt install git"
chk "lsusb"   "command -v lsusb"   "sudo apt install usbutils"
chk "picocom(串口终端)" "command -v picocom" "sudo apt install picocom"

echo
echo "═══ Python ═══"
if command -v python3 >/dev/null 2>&1; then
    pyver=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
    if python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)'; then
        printf "  ${G}✓${N} python3 %s\n" "$pyver"; ok=$((ok+1))
    else
        printf "  ${R}✗${N} python3 %s 太旧(要 ≥3.8)\n" "$pyver"; bad=$((bad+1))
    fi
else
    printf "  ${R}✗${N} python3 没装\n     ${Y}→ sudo apt install python3${N}\n"; bad=$((bad+1))
fi

echo
echo "═══ Python 包(tethered boot 的 proxyclient 要用)═══"
chk "pyserial(import serial)" \
    "python3 -c 'import serial'" \
    "Ubuntu: sudo apt install python3-serial / 其他: pip3 install --user pyserial"
chk "construct(import construct)" \
    "python3 -c 'import construct'" \
    "Ubuntu: sudo apt install python3-construct / 其他: pip3 install --user construct"
printf "     ${Y}注${N}: Ubuntu 24.04 起 pip3 --user 会被 PEP 668 拦,用 venv 或加 --break-system-packages\n"
printf "     ${Y}注${N}: 别装 PyPI 的 serial.tool —— m1n1 要的 serial.tools 由 pyserial 提供\n"
printf "          (serial.tool 是个无关的小包; 写上它纯属多余且可能误导)\n"

echo
echo "═══ Rust(m1n1 有 Rust 部分,别漏)═══"
chk "rustup" "command -v rustup" \
    "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
chk "rust target aarch64-unknown-none-softfloat" \
    "rustup target list --installed 2>/dev/null | grep -q aarch64-unknown-none-softfloat" \
    "rustup target add aarch64-unknown-none-softfloat"

echo
echo "═══ USB ═══"
# 注:之前这里把 libusb 当必需项 —— 查过 m1n1 仓库,**它一处都没引用 libusb**
# (proxyclient 走 pyserial 读 ttyACM,不经 libusb)。所以不做硬性检查。
printf "  ${Y}注${N}: m1n1 proxyclient 用 pyserial 读 /dev/ttyACM*,不需要 libusb。\n"
printf "      若某个脚本报缺 libusb,再 sudo apt install libusb-1.0-0-dev 不迟。\n"

if [ -d /sys/class/typec ] && [ -n "$(ls -A /sys/class/typec 2>/dev/null)" ]; then
    printf "  ${G}✓${N} 检测到 USB-C 控制器\n"; ok=$((ok+1))
else
    printf "  ${Y}!${N} 没看到 /sys/class/typec\n"
    printf "      ${Y}→ 可能这台的 USB-C 走别的方式;用 USB-A 口的话记得转接线要是数据线${N}\n"
fi

echo
echo "═══ 磁盘空间(内核源码 + 构建产物,建议 ≥20 GB)═══"
avail=$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2{print int($4/1048576)}')
if [ -n "${avail:-}" ] && [ "$avail" -ge 20 ]; then
    printf "  ${G}✓${N} \$HOME 可用 %s GB\n" "$avail"; ok=$((ok+1))
else
    printf "  ${R}✗${N} \$HOME 可用 ${avail:-?} GB(要 ≥20)\n"; bad=$((bad+1))
fi

echo
echo "═══ 还没法在这里检查的(等 m1n1 拉下来再说)═══"
echo "  · m1n1 的 udev 规则 —— 装完 m1n1 后按它的 README 装,否则 USB 访问会被拒"
echo "  · 拉源码记得加 --recursive(有子模块)"
echo "  · 数据线是不是数据线 —— 只能靠插上试"
echo
echo "────────────────────────────────────────"
if [ "$bad" -eq 0 ]; then
    printf "${G}全绿(%d 项)。${N}可以去读 PLAYBOOK 的 M1 了。\n" "$ok"
    exit 0
else
    printf "${R}还有 %d 项没满足${N}(通过 %d 项)。把上面的 → 逐条做掉再来。\n" "$bad" "$ok"
    exit 1
fi
