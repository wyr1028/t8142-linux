# m5linux

在 Apple M5 上运行 Linux 的**独立**移植项目。

> **与 Asahi Linux 完全无关。** 本项目不向其提交任何内容、不与其合并、不在其频道出现。
> 该项目的政策禁止 AI 参与,而本项目声明使用 AI —— 两者从设计上就是隔离的。
> 它是 GPL 公开代码,读它是 GPL 给的权利;但本项目只做自己的东西。

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
| **原始 ADT dump** | ❌ 需要 tethered boot,**缺第二台机器** |
| 引导链(m1n1) | ❌ 未动 |
| 设备树 | ❌ 空白,M5 在上游无任何 DTS |
| 内核引导 | ❌ 未动 |

**当前唯一阻塞点**:没有第二台能连 USB-C 的机器。其余全部依赖它。

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
  RISKS.md           实操风险:机器 / 数据 / 时间(讲技术,不讲法律)
tools/
  adtlib.py          ADT 读取层(ioreg plist + 原始 FDT 两种输入)
  adt2dts.py         ADT → DTS 骨架 / 列 compatible / 找节点
  compat_diff.py     compatible 差集(复现 docs/HARDWARE.md §4)
  adt_report.py      硬件清单生成(markdown)
tests/
  test_adtlib.py     自测 + dtc 交叉验证(FDT 路径的唯一覆盖)
dts/                 t8142*.dts* / t8142-j704.dts
```

## 许可证

**GPL-2.0-or-later**。理由:设备树与内核驱动是 Linux 的衍生,必须同许可。
不要在未确认兼容性前引入任何其他许可证的代码。

## 原则

1. **只用自己机器上的观测 + 公开资料。** 见 LEGAL.md。
2. **每条事实记来源。** 见 docs/PROVENANCE.md。
3. **不声称 clean room,不做法律主张。**
4. **先验证,再下结论。** 猜出来的东西标成"未验证",别混进事实表。
