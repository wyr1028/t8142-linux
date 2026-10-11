# 来源日志

> **这是本项目最重要的合规资产。**
> 它证明我们没有依赖任何未公开资料,也给以后可能出现的争议留下证据链。

## 记什么

每条技术事实一行。要能回答:**谁、在哪台机器上、跑了什么、得到什么。**

**AI 的输出不算来源。** AI 说的东西必须回到下面三类之一去验证,验证结果才是来源。

## 允许的来源

1. **自己机器上的输出** —— 命令 + 原始结果
2. **公开资料** —— 上游 GPL 代码、Apple 公开文档、公开发布的演讲
3. **由 1 或 2 可复现地推导** —— 推导过程要写下来

## 禁止的来源

- 泄露的 Apple 内部资料(iBoot / ATF / XNU 源码、内部文档、原理图)
- 无法说明来源的文件
- 凭印象、"我记得"、"AI 说的"

---

## 日志

| 日期 | 事实 | 类型 | 具体来源 | 可复现 |
|---|---|---|---|---|
| 2026-10-11 | 机型 / 芯片 / 核数 / 内存 | 真机 | `sysctl hw.model machdep.cpu.brand_string hw.ncpu hw.memsize` @ Mac17,2 | ✅ |
| 2026-10-11 | macOS 版本 / build | 真机 | `sw_vers` | ✅ |
| 2026-10-11 | 固件版本 / Secure Boot 状态 | 真机 | `system_profiler SPHardwareDataType SPiBridgeDataType`(序列号已过滤) | ✅ |
| 2026-10-11 | ADT 拓扑(527 节点)+ compatible 全集 | 真机 | `ioreg -a -p IODeviceTree -l` @ Mac17,2 | ✅ |
| 2026-10-11 | 核 compatible:`apple,sawtooth`(cpu0-5)/ `apple,everest`(cpu6-9) | 真机 | 同上,解析 cpu 节点 `compatible` 属性 | ✅ |
| 2026-10-11 | m1n1 对 M5 的支持范围(SoC id / UART base / MIDR / SMP) | 公开 | `AsahiLinux/m1n1` HEAD `7f20877` 源码:`soc.h` `midr.h` `chickens.c` `smp.c` | ✅ |
| 2026-10-11 | PR #629 `Initial support for T8142`(2026-07-19 合并) | 公开 | GitHub API `repos/AsahiLinux/m1n1/pulls/629` | ✅ |
| 2026-10-11 | PR #578 pmgr 覆盖 M4 Pro/Max、A18 Pro、M5 | 公开 | GitHub API `.../pulls/578` | ✅ |
| 2026-10-11 | m1n1 中 M5 未引用的 25 个 compatible | 推导 | 真机 ADT compatible 集 △ 公开源码字面量集;差集脚本可重跑 | ✅ |
| 2026-10-11 | M4 设备树规模(`t8132.dtsi` 440 行 / `t8132-pmgr.dtsi` 1125 行 / 129 power-state) | 公开 | GitHub API `repos/AsahiLinux/linux/contents/arch/arm64/boot/dts/apple/`(分支 `asahi`) | ✅ |
| 2026-10-11 | M4 核 compatible = `apple,donan-e` / `apple,donan-p` | 公开 | 同上,`t8132.dtsi` | ✅ |
| 2026-10-11 | M5(`t8142`)在 Linux DTS 中不存在 | 公开 | 同上,目录列表无 `t8142*` | ✅ |
| 2026-10-11 | **更正**:m1n1 未引用的 compatible 总数是 39,其中带 `,t8142` 的 25 条、复用旧代号的 14 条。此前口述的"25"是后者的子集,不是全部 | 推导 | `tools/compat_diff.py ~/m5-adt.plist <repo>/src --soc t8142` | ✅ |
| 2026-10-11 | PMGR 的 power-state 编码在 `/arm-io/pmgr` 的 `devices` 二进制属性里(18576 字节),不是节点 | 真机 | 解析 ioreg dump 的 pmgr 节点属性表 | ✅ |
| 2026-10-11 | `devices` blob 内含 335 个唯一电源域名字(`ACTIVE` `ECPU_0` `AMCC0_P0` `AOP_DART` …) | 真机 | 从上述 blob 抽 NUL 结尾字符串 | ✅ |
| 2026-10-11 | `devices` 条目疑似定长,名字在固定偏移(前两个在字节 32 与 84) | 真机 | 观察 blob 前 96 字节 hex | ⚠️ 结构未确证 |
| 2026-10-11 | FDT 解析器正确性 | 推导 | `tests/test_adtlib.py`,含用 **dtc**(独立实现)生成的 DTB 交叉验证 | ✅ |

---

## AI 工具链

| 项 | 值 |
|---|---|
| 客户端 | Claude Code |
| 后端模型 | DeepSeek 系列(会话环境标识 `deepseek-flash`) |
| 角色 | 起草文档 / 脚本 / 代码;**不接触任何未公开资料** |
| 人类职责 | 逐条验证后才进入本项目 |

> 模型与版本随工具更新会变,以当时的会话记录为准。

---

## ⚠️ 与 Asahi 项目的关系(必须写清)

- m1n1 / linux-asahi 的**源码是公开 GPL,读它们合法**,已记入上表
- 但**本项目不向其提交任何内容**、不与其合并、不在其频道出现
- 理由:那边明令禁止任何 AI 参与(法律原因,clean room 证据链),
  而本项目声明使用 AI([../AI-USAGE.md](../AI-USAGE.md)) —— 两者从设计上不相容
- 因此:本项目的任何产出**永远不回上游**,这一点在立项时就接受

---

## 模板(新增事实时复制)

```
| YYYY-MM-DD | 事实 | 真机 / 公开 / 推导 | 命令或文件路径 + commit/版本 | ✅/❌ |
```
