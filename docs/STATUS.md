# 进度总览

一页看完:这项目是什么、到哪了、卡在哪、下一步。

---

## 一句话

让 **Linux 原生跑在 Apple M5**(本机 MacBook Pro 14",`Mac17,2` / 板号 J704 / SoC `t8142`)上。
**独立项目,不与 Asahi Linux 合并,不向其提交任何东西。**

---

## 现在到哪了

```
[██████░░░░░░░░░░░░░░]  准备阶段基本做完,真机一步没动
```

**真机工作一步都没开始** —— 卡点只有一个:**没有第二台电脑**(tethered boot 需要)。

在此之前所有能做的纸面工作已做完。

---

## 哪个问题最要紧:已答

| 问题 | 答案 |
|---|---|
| M5 的 PMGR 和 M4 差多少? | 名字重合 **92%**,偏移重合 **6%** |
| 那要几年? | **月级,不是年级** —— 结构能抄,数值可算 |
| 怎么算? | `tools/pmgr_join.py` 做一次表连接,已产出 `dts/t8142-pmgr.dtsi` |

---

## 已有产物

**工具**(`tools/`,全部有测试,`make test`)

| 工具 | 干什么 |
|---|---|
| `adtlib.py` | ADT 读取层(ioreg plist + 原始 FDT) |
| `adt2dts.py` | ADT → DTS 骨架 / 列 compatible / 找节点 |
| `compat_diff.py` | compatible 差集(回答"M5 上哪些块是新的") |
| `adt_report.py` | 硬件清单生成 |
| `pmgr_devices.py` | PMGR `devices` 属性解码(387 条 → 141 条真实域) |
| `pmgr_join.py` | M4 结构 + M5 数值 → `t8142-pmgr.dtsi` 草稿 |
| `scrub_adt.py` | 洗敏感字段 + 发布前自查 |

**文档**(`docs/`)

| 文件 | 内容 |
|---|---|
| `HARDWARE.md` | M5/J704 硬件事实,每条带来源与置信度 |
| `PMGR-DEVICES.md` | `devices` 属性结构 + **地址结构已解开** |
| `PMGR-DELTA.md` | **M5 vs M4 全面对照 —— 回答"几个月还是几年"** |
| `PLAYBOOK.md` | M0→M7 操作手册,每步带命令与判据 |
| `RISKS.md` | 实操风险(机器/数据/时间) |
| `DEPENDENCIES.md` | 依赖侵权审查 |
| `PROVENANCE.md` | 来源日志 —— 合规资产 |

---

## 卡在哪

**硬件。** 机器都已经有了,**不需要买**:

| 角色 | 机器 | 状态 |
|---|---|---|
| Linux 主机 | **游戏本 → 装 Ubuntu LTS 双系统** | ⬜ 待装 |
| DFU 兜底 | **M3 MacBook Air 15" → 装 Apple Configurator 2** | ⬜ 待装 |
| 数据线 | USB-C **数据线**(不是充电线) | ⬜ 待确认 |
| 备份 | M5 的 Time Machine,且验证过能恢复 | ⬜ 待做 |

**唯一实打实的准备动作是给游戏本装 Linux。** 装完就能进 `PLAYBOOK.md` 的 M1。

---

## 不等硬件还能做什么

| 还能做 | 价值 |
|---|---|
| 人工校对 `dts/t8142-pmgr.dtsi` 的 30 条新条目 | 中 |
| ~~M4 → M5 的非 PMGR 块对照~~ | ✅ **已做**,见 [DTS-BACKLOG](DTS-BACKLOG.md) |

**对照做完后结论变了**:

- M4 的**整套** Linux 支持只有 **440 行**(就是"内核能跑 + 串口能说话")
- M4 板级文件只有 **35 行**
- M5 需要的 14 个节点,**ADT 里一个不缺,地址全有**

所以剩下的活**不是工作量问题,是三个格式问题**([DTS-BACKLOG](DTS-BACKLOG.md) §3):

1. `reg` 的 cell 格式(M4 的 DT 与 M5 的 ADT 对不上)
2. CPU 的 compatible 到底叫什么(三源打架)
3. AIC 中断号怎么编

**这三个都只能在真机上问清楚。纸面工作到此为止 —— 下一步必须是机器。**

---

## 三条必须守住的

1. **不碰任何 Apple 未公开资料**(唯一红线)
2. **外发前过 `scrub_adt.py --verify`**(原始 dump 有 87 处敏感字段)
3. **不声称 clean room** —— 本项目声明使用 AI,见 [AI-USAGE](../AI-USAGE.md)
