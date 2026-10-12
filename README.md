# t8142-linux

在 Apple M5 上运行 Linux 的**独立**移植项目。

> # ⛔ 项目已停止(2026-10-12)
>
> **不做了。** 卡在最后一步 —— 让 m1n1 拥有一个**独立启动项**。
>
> ## 卡在哪
>
> 两条路都走不通:
>
> | 路线 | 做法 | 为什么停 |
> |---|---|---|
> | **写 macOS 卷** | `kmutil -v "/Volumes/Macintosh HD - Data"` | **同机 J704 实测走通过**,但代价是「启动器里选 macOS 也跑 m1n1」。**不接受这个代价** |
> | **独立 stub 卷** | 在另一个容器建「假 macOS」给 m1n1 挂靠 | **卡在 `bless`** —— 详见下 |
>
> 第二条路本来是对的选择(不碰 macOS),而且**建 stub 那段已经全做通了**:
> 卷组建成、macOS 启动文件铺好、m1n1 编译出来、装成 `boot.bin`、**1TR 里能看到
> "Linux"、能进去、`step2.sh` 会自动跑**。卡死在最后一个环节:
>
> ```
> bless --setBoot --device /dev/<stub System> --user <u> --stdinpass
>   → BootabilityService: Failed to mount source preboot
>     mount_apfs returned : 66  (EPERM)
> ```
>
> 由此形成死结:
>
> ```
> bless 失败 → 不成为默认启动卷 → stub 的 recoveryOS 不是 1TR
>                                    ↓
>                          bputil 拒绝改策略(AP boot mode)
>                                    ↓
>                         拿不到 LocalPolicy → stub 永远起不来
> ```
>
> 两个环境的实测错误码(可复现):macOS 的 1TR 里 `pairing (17)`;
> stub 自己的 recoveryOS 里 `AP boot mode (11)`。**两头都不通。**
>
> ## 为啥判定"不值得再挖"
>
> 堵点在 **Apple 私有框架内部**(`BootabilityBrain.framework` / `com.apple.bootpolicy`),
> 不是命令用法问题。已经试过:挖 `bless` / `BootabilityService` 二进制、
> 用 Apple 留的调试开关 `BYDisablePrebootBrain`(XPC 服务收不到)、
> `fs_usage` 跟踪(被 SIP 挡)、多组参数、对照实验 —— 全部无效。
> 再往下需要动 macOS 自己在用的卷,风险性质变了。
>
> **决定性的一条:M5 + macOS 27 这个组合,全网没有任何成功记录。**
> Asahi 的用户能过,是因为他们机器上这条路本来就通。
>
> **顺带**:Asahi 的 `stub.py` 是按 macOS ≤14 写的,27 上有三处必须适配
> (`bless2.RestoreBundlePath` 键被删 / `pbzm` 取代 `pbzx` / `BaseSystem.dmg`
> 改从本机 Recovery 卷拷)—— **这三处已经解决并留档**,见
> [docs/STUB-INSTALL.md](docs/STUB-INSTALL.md)。
>
> ## 机器状态
>
> **M5 已恢复原样**:stub 容器(disk4)删除、114 GB 还给 macOS;
> boot policy 与 SIP 经逐字对照确认**未受影响**;本机所有原料已清空。
> **仓库保留**,随时可以 `git clone` 接着走。
>
> ---

> **`t8142` 是什么**:Apple M5 的 SoC 代号(从本机设备树里读出来的)。
> 项目名用代号而不是 `m5`,是为了避开 Apple 商标。

**目标机器**:MacBook Pro 14"(`Mac17,2`,板号 J704),Apple M5。

> ## 项目定位:**能用,但不合并**
>
> - ✅ **可以使用任何项目的任何东西** —— 依赖、工具、安装器、公开代码,全都可以
> - ❌ **但绝不向上游合并 / 提交任何内容**,也不在其频道出现
>
> 换句话说,**约束只有一条:不回馈。不是"不能碰"。**
>
> **起因**:上游明令禁止任何 AI 参与(法律理由 = clean room 证据链),
> 而本项目声明使用 AI(见 [AI-USAGE.md](AI-USAGE.md))—— 所以从设计上就是隔离的。
> 这不是"我们不想用他们的东西",是"我们产出的东西不能回到那边去"。

## 🔄 接手这个项目(换一台机器 / 换一个 AI)

**只看这一节 + [docs/STATUS.md](docs/STATUS.md) 就够了。**

> **两台机器轮流改,不是单向同步。** 每台机器**动手前先 `git pull`**,
> 做完就 `commit` + `push`。这台推的,那台拉;那台推的,这台拉。

1. `git clone <repo>`(已公开,不需要账号权限)
2. **读 `docs/STATUS.md`** —— 一页看完:到哪了 / 卡在哪 / 下一步
3. 读 `docs/PROVENANCE.md` —— **每个技术事实的来源**,接手前必读
4. 按 `docs/ROADMAP.md` 的 `[ ]` 往下做;具体命令在 `docs/PLAYBOOK.md`

**这个仓库是自解释的**:状态、卡点、下一步都在仓库里,不依赖任何对话上下文。
做一块就提交一块 —— 接手的是另一台机器上的 AI,它只有这个仓库。

> **网络提示(国内)**:直连 `github.com:443` 常常不通,但 `api.github.com` 通常能通。
> 表现是:`gh` 命令正常,`git push` 超时。push 时挂代理即可:
>
> ```bash
> git -c http.proxy=http://127.0.0.1:7897 push
> ```
>
> 端口换成你自己代理的(实测 7897 是 Clash 系的常用口)。
>
> **改历史后要强推**:`git push --force` —— 本仓库单人维护,没有协作冲突问题。

> **提交身份**:全部提交使用 GitHub 的 noreply 邮箱
> (`119118918+wyr1028@users.noreply.github.com`),不是真实邮箱。
> 新提交前确认 `git config user.email` 正确。

---

## 目标

| 项 | 值 |
|---|---|
| 目标机器 | MacBook Pro 14" (`Mac17,2`),板号 **J704** |
| SoC | **`t8142`** |
| 目标 | 裸机启动 Linux,推进到可用 |

## 现状

| 项 | 状态 |
|---|---|
| 真机侦察(ADT 拓扑 / compatible) | ✅ 已采(2026-10-11) |
| 地址翻译规则 | ✅ 已解:**+`0x2_1000_0000`** |
| M5 先例调查 | ✅ 见 [docs/M5-PRIOR-ART.md](docs/M5-PRIOR-ART.md) |
| **原始 ADT dump** | ❌ 需要 tethered boot,**缺 Linux 主机** |
| 引导链(m1n1) | ❌ 未动(m1n1 有 T8142 初始支持) |
| 设备树 | ⚠️ **上游已有两份**(rhelvista / sentaxic),但**互相打架**,需真机验 |
| 内核引导 | ❌ 未动(M4 上已有人跑到 shell) |
| AICv3(`aic,3`) | ✅ **已支持**(M3/M4 同款,`apple,t8122-aic3`) |

**当前唯一阻塞点**:Linux 主机(游戏本装 Ubuntu)还没好。

## 先读这三份

| 文件 | 内容 |
|---|---|
| [LEGAL.md](LEGAL.md) | **动手前必读** —— 红线、黄线、绿线 |
| [AI-USAGE.md](AI-USAGE.md) | AI 使用声明 |
| [ROADMAP.md](ROADMAP.md) | 工作清单(要做什么) |
| [docs/PLAYBOOK.md](docs/PLAYBOOK.md) | 操作手册(具体怎么做,命令级) |

## 目录

```
README.md            本文件
LEGAL.md             法律与风险边界(讲法律)
AI-USAGE.md          AI 使用声明
ROADMAP.md           工作清单 —— 要做什么
LICENSE              GPL-2.0-or-later(官方原文 + 选用说明)
Makefile             make test / check / lint-trailing
docs/
  HARDWARE.md        M5/J704 硬件事实(每条带来源与置信度)
  PROVENANCE.md      来源日志 —— 本项目最重要的合规资产
  PLAYBOOK.md        M0→M7 操作手册,每步带命令与判据
  M1-RUNBOOK.md      M1(点亮 m1n1)的逐条手册 —— 会动 boot policy 的那步
  RISKS.md           实操风险:机器 / 数据 / 时间(讲技术,不讲法律)
  DEPENDENCIES.md    依赖侵权审查:每个外部依赖的许可证与风险
  PMGR-DEVICES.md    PMGR `devices` 属性的结构解码(含来源诚实说明)
  PMGR-DELTA.md      M5 vs M4 的 PMGR 差异 —— 回答"几个月还是几年"
  STATUS.md          一页看完:到哪了 / 卡在哪 / 下一步
  DTS-BACKLOG.md     M4 到底做了多少(440 行)/ M5 缺什么 / 三个格式问题
  M5-PRIOR-ART.md    M5 上有没有人做过了 —— 现有工作、地址规则、真正的难点
  OFFICIAL-TETHERED-BOOT.md  官方 tethered boot 文档要点(权威版本)
  M5-MEMMAP.md       M5/J704 内存映射(从原始 ADT 生成, 已交叉验证)
  IOREG-CAVEATS.md   ⚠️ ioreg 视图的三条陷阱(合成/展开/固件版本差异)
  EXTRACT-ADT.md     ⭐ 从本机 macOS 提取 ADT —— **不用 m1n1**
  HOW-TO-UNDO.md     ⚠️ 装了 m1n1 之后怎么回 macOS + NOR Flash 红线
  PROXY-ZEROS.md     "proxy 读出全是 0" 的误诊分析 + 窗口假设
tools/
  adtlib.py          ADT 读取层(ioreg plist + 原始 FDT 两种输入)
  adt2dts.py         ADT → DTS 骨架 / 列 compatible / 找节点
  compat_diff.py     compatible 差集(复现 docs/HARDWARE.md §4)
  adt_report.py      硬件清单生成(markdown)
  pmgr_devices.py    PMGR `devices` 属性解码(387 条电源域)
  pmgr_join.py       M4 结构 + M5 数值 → t8142-pmgr.dtsi 草稿
  scrub_adt.py       洗敏感字段 + 发布前自查(--verify)
  check_host.sh      在 Linux 主机上跑的自检(装完系统后验一遍)
dts/
  t8142-pmgr.dtsi    生成的草稿(135 条;dtc 编译通过)
tests/
  test_adtlib.py     自测 + dtc 交叉验证(FDT 路径的唯一覆盖)
  test_pmgr_devices.py  PMGR 结构自测
  test_pmgr_join.py     断言生成的 dtsi 无重复节点地址
  test_scrub_adt.py     洗敏感字段 + 自查误报(两个踩过的坑)
```

## 许可证

**GPL-2.0-or-later**。理由:设备树与内核驱动是 Linux 的衍生,必须同许可。
不要在未确认兼容性前引入任何其他许可证的代码。

## 原则

1. **只用自己机器上的观测 + 公开资料。** 见 LEGAL.md。
2. **每条事实记来源。** 见 docs/PROVENANCE.md。
3. **不声称 clean room,不做法律主张。**
4. **先验证,再下结论。** 猜出来的东西标成"未验证",别混进事实表。
