# 真实游戏手动验证台账

本文汇总哪些能力已经在目标 Mac 上的原版 Civilization V: Campaign
Edition 对局中实际验证。它是便于快速阅读的状态表，不保存原始输出。

- 详细环境、步骤和观察证据以 [实验日志](../EXPERIMENT_LOG.md) 为准。
- 离线测试结果以 [测试矩阵](TEST_MATRIX.md) 为准。
- 下一次操作步骤以 [实机测试清单](../LIVE_TEST_CHECKLIST.md) 为准。

## 状态定义

| 状态 | 含义 |
|---|---|
| 已实机验证 | 在真实对局中观察到预期结果，并完成必要的恢复检查 |
| 部分实机验证 | 主路径在真实对局出现过，但新增字段、边界或完整证据仍缺失 |
| 待实机验证 | 已实现并通过离线测试，但尚未在真实对局执行 |
| 已否决 | 已在目标环境尝试，证据表明该方案不可行或不应采用 |

“代码已经实现”“检查过游戏自带 Lua”“离线测试通过”和“已实机验证”
是不同证据等级，不能互相替代。

## 已实机验证

| 能力 | 日期 | 真实游戏中观察到的结果 | 证据 |
|---|---|---|---|
| 原版 FireTuner 状态读取 | 2026-09-12 | 外部 Python 读取到与游戏界面一致的回合、玩家和金币 | [FireTuner 读取实验](../EXPERIMENT_LOG.md#2026-09-12--firetuner-in-game-read-proof) |
| 持久 watcher 与丰富状态读取 | 2026-09-12 | 单一持久连接持续读取城市、科研、经济和单位变化 | [MVP 实验](../EXPERIMENT_LOG.md#2026-09-12--rich-read-and-verified-end-turn-mvp) |
| `end_turn` | 2026-09-12 | 回合从 0 推进到 1，返回写前/写后状态并回读确认 | [MVP 实验](../EXPERIMENT_LOG.md#2026-09-12--rich-read-and-verified-end-turn-mvp) |
| schema 2 | 2026-09-12 | 读取回合状态、城市、单位、科研和回合结束条件 | [schema 2 实验](../EXPERIMENT_LOG.md#2026-09-12--schema-2-research-production-and-controller-live-proof) |
| `choose_research` | 2026-09-12 | 从未选择科研变为 Pottery，并回读技术 ID、进度和成本 | [schema 2 实验](../EXPERIMENT_LOG.md#2026-09-12--schema-2-research-production-and-controller-live-proof) |
| `set_city_production` | 2026-09-12 | 空生产队列变为 Scout，并通过状态回读确认 | [schema 2 实验](../EXPERIMENT_LOG.md#2026-09-12--schema-2-research-production-and-controller-live-proof) |
| 非法结束回合拒绝 | 2026-09-12 | 单位仍需命令时，结束回合被拒绝且回合状态不变 | [schema 2 实验](../EXPERIMENT_LOG.md#2026-09-12--schema-2-research-production-and-controller-live-proof) |
| 旧 controller 的就绪检查证明 | 2026-09-12 | dry-run 指出必选事项；显式执行后验证回合推进；不代表未来 M6 战术策略 | [schema 2 实验](../EXPERIMENT_LOG.md#2026-09-12--schema-2-research-production-and-controller-live-proof) |
| FireTuner 安全边界与恢复 | 2026-09-12 | 防火墙临时开启、Civ V 入站被阻止；测试后配置、端口、socket 和防火墙恢复 | [schema 2 实验](../EXPERIMENT_LOG.md#2026-09-12--schema-2-research-production-and-controller-live-proof) |
| 只读安全预检 | 2026-09-13 | 恢复后的主机通过 shutdown 检查：FireTuner 关闭且无监听端口和 agent socket | [预检实验](../EXPERIMENT_LOG.md#2026-09-13--read-only-safety-preflight) |
| schema 4 分段读取 | 2026-09-14 | 读取分数、时代、城市经济、单位状态及早期外交/胜利分支；分段长度受限并检查回合/玩家一致性 | [分段读取实验](../EXPERIMENT_LOG.md#2026-09-14--segmented-live-state-and-corrected-unit-skip-proof) |
| `skip_unit` | 2026-09-14 | readiness 从 true 变为 false，单位 ID、坐标及剩余移动力不变，自动回读返回成功 | [单位跳过实验](../EXPERIMENT_LOG.md#2026-09-14--segmented-live-state-and-corrected-unit-skip-proof) |
| schema 5 普通科技状态 | 2026-09-15 | 已研究/可研究集合与游戏界面一致；普通科研从待选择变为已选择后，当前科研及 `required` 同步变化 | [科技状态实验](../EXPERIMENT_LOG.md#2026-09-15--schema-5-ordinary-technology-state-live-proof) |

## 部分实机验证

| 能力 | 已有证据 | 尚缺证据 |
|---|---|---|
| 命令 UUID、审计与重复抑制 | 真实写入命令曾返回 UUID，核心写入路径已运行 | 新的参数审计和同 UUID 重放保护主要是离线验证；需要时再设计不产生二次游戏写入的受限实验 |
| schema 4：外交非空分支 | 未接触任何主要文明时已确认列表为空 | 遇到主要文明后确认只返回已接触对象 |
| schema 4：科学胜利非零分支 | 启用标志及五个早期零进度计数已读取 | 用合适后期存档确认非零项目计数 |
| schema 5：特殊科技选择模式 | 普通科研模式已经实机验证；免费/窃取模式的 API 与控制器拒绝路径已离线测试 | 在自然出现且可安全复现的免费科技或窃取科技场景中验证；保持手动处理 |
| M5 对局事实日志 | 首次联合测试已实机确认 schema 5 捕获、哈希链、连续回放、结构导出、私有权限及人工回合转换 | 执行异常只留下提交记录，暴露生命周期缺口；已离线增加未知结果验证错误，仍需复测完整命令生命周期 |
| M6 确定性回合执行器 | 显式单动作 TurnPlan 已在真实 watcher 会话中创建并通过只读校验 | `end_turn` Lua 超过目标传输上限而被截断；已离线压缩并加上限/保守恢复，仍需复测实际执行 |

## 待实机验证

| 能力 | 离线状态 | 下一次真实游戏测试 |
|---|---|---|
| M5 对局事实日志 | 私有追加存储、哈希链、验证、顺序回放、脱敏结构导出及未知结果记录均已通过离线测试 | 重复 M8 联合清单，要求快照、提交、终端结果和回合转换形成完整生命周期 |
| M6 确定性回合执行器 | 显式 TurnPlan 的校验、执行、暂停、陈旧状态、程序上限和未知结果恢复路径均已通过离线测试 | 用压缩后的 `end_turn` 程序重复单次执行，要求完整报告与自动回合推进 |
| 坐标移动 | 尚未实现 | 先设计路径、所有权、合法性与明确写后条件，不进入当前测试范围 |

M5/M6 联合实机验证是 M8 发布门槛，需要用户在场，具体命令见实机测试
清单第 6 节。免费科技与窃取科技分支保持待验证和手动处理；外交非空
与科学胜利非零仍属于增强证据。

## 已否决的实机方案

| 方案 | 结论 | 证据 |
|---|---|---|
| 从 Campaign Edition 主菜单启用自定义 Mod | 游戏能发现 Mod，但厂商隐藏了受支持的启用入口 | [自定义 Mod 实验](../EXPERIMENT_LOG.md#2026-09-12--phase-0-custom-lua-mod-loading-attempt) |
| 修改复制的签名应用以显示 Mods 按钮 | macOS 完整性检查将修改后的应用判定为损坏 | [应用副本实验](../EXPERIMENT_LOG.md#2026-09-12--modified-application-copy-launch-attempt) |
| 在防火墙关闭时暴露 FireTuner | 服务监听 `*:4318`，不能作为安全测试配置 | [暴露与恢复实验](../EXPERIMENT_LOG.md#2026-09-12--firetuner-exposure-and-safe-shutdown) |

## 每次手动测试后的更新规则

1. 先把完整环境、步骤、实际观察、结论和恢复状态追加到实验日志。
2. 更新本台账中对应能力的状态和简要结论。
3. 更新测试矩阵的 Target Mac 与 Current status 两列。
4. 若项目当前状态或下一步因此改变，再更新 `PROJECT_STATE.md`。
5. 只提交脱敏结论；不得提交玩家姓名、存档数据、原始快照、本地绝对
   路径、命令审计日志或 FireTuner 原始输出。
