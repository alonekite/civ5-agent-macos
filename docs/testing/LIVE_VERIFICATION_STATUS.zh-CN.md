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
| 持久主机加固 | 2026-09-21 | 一次性记录原始防火墙/规则基线，启用防火墙并永久阻止 Civ V 入站；随后独立 `hardened` 预检确认 FireTuner、端口和 watcher 均关闭 | [持久加固实验](../EXPERIMENT_LOG.md#2026-09-21--persistent-host-hardening-installation-proof) |
| schema 4 分段读取 | 2026-09-14 | 读取分数、时代、城市经济、单位状态及早期外交/胜利分支；分段长度受限并检查回合/玩家一致性 | [分段读取实验](../EXPERIMENT_LOG.md#2026-09-14--segmented-live-state-and-corrected-unit-skip-proof) |
| `skip_unit` | 2026-09-14 | readiness 从 true 变为 false，单位 ID、坐标及剩余移动力不变，自动回读返回成功 | [单位跳过实验](../EXPERIMENT_LOG.md#2026-09-14--segmented-live-state-and-corrected-unit-skip-proof) |
| schema 5 普通科技状态 | 2026-09-15 | 已研究/可研究集合与游戏界面一致；普通科研从待选择变为已选择后，当前科研及 `required` 同步变化 | [科技状态实验](../EXPERIMENT_LOG.md#2026-09-15--schema-5-ordinary-technology-state-live-proof) |
| M5 对局事实日志 | 2026-09-16 | 同一私有 journal 完整记录成功命令与自动回合转换；哈希链、连续回放、结构导出、`0600` 权限及恢复均通过 | [M5/M6 成功实验](../EXPERIMENT_LOG.md#2026-09-16--combined-m5m6-release-gate-successful-attempt) |
| M6 确定性回合执行器 | 2026-09-16 | 新建并校验单动作显式计划；单次执行返回 `completed`，游戏与 watcher 均确认自动推进一个回合 | [M5/M6 成功实验](../EXPERIMENT_LOG.md#2026-09-16--combined-m5m6-release-gate-successful-attempt) |
| schema 6 相邻普通移动 | 2026-09-17 | 源坐标请求在写入前被拒绝；另行授权的一次相邻空地移动到达精确目标、移动力下降，watcher 捕获新快照且无额外副作用；审计权限与主机恢复通过 | [移动实机实验](../EXPERIMENT_LOG.md#2026-09-17--schema-6-adjacent-movement-live-proof) |
| schema 7 与 `worker_build` | 2026-09-19 | 候选与 UI 一致且读取无副作用；错误源坐标在写前拒绝；另行授权的一次矿场建造进入精确 active-build 状态、移动力下降，watcher 与 UI 一致且无额外副作用；私有审计与主机恢复通过 | [工人建造实机实验](../EXPERIMENT_LOG.md#2026-09-19--schema-7-worker-build-successful-active-build-proof) |
| schema 8 普通科研运行时事实 | 2026-09-21 | 同一 bridge session 跨越两次回合结算；精确进度、UI、正溢出、选择时保留及下一回合应用均一致；私有审计零记录且主机完整恢复 | [科研运行时实机实验](../EXPERIMENT_LOG.md#2026-09-21--schema-8-same-session-controlled-overflow-proof) |

## 部分实机验证

| 能力 | 已有证据 | 尚缺证据 |
|---|---|---|
| 命令 UUID、审计与重复抑制 | 真实写入命令曾返回 UUID，核心写入路径已运行 | 新的参数审计和同 UUID 重放保护主要是离线验证；需要时再设计不产生二次游戏写入的受限实验 |
| schema 4：外交非空分支 | 未接触任何主要文明时已确认列表为空 | 遇到主要文明后确认只返回已接触对象 |
| schema 4：科学胜利非零分支 | 启用标志及五个早期零进度计数已读取 | 用合适后期存档确认非零项目计数 |
| schema 5：特殊科技选择模式 | 普通科研模式已经实机验证；免费/窃取模式的 API 与控制器拒绝路径已离线测试 | 在自然出现且可安全复现的免费科技或窃取科技场景中验证；保持手动处理 |
| 持久加固会话生命周期 | `harden` 与独立 `preflight hardened` 已通过，保护状态保留在主机上 | 下次实机测试证明 `prepare/restore` 只切换 FireTuner 并保留防火墙规则；仅在用户确实要撤销加固时验证 `unharden` |

## 待实机验证

当前没有阻塞 M10 的待实机项目。`worker_build` 的 immediate-completion
分支保留离线证据，不需要为了覆盖另一成功分支再执行一次真实写入。

M5/M6 联合实机发布门槛、M9 C6 相邻普通移动门槛、M10 C6 工人建造
门槛和 M11 C4 科研运行时事实门槛均已完成；相应清单保留为回归程序。
免费科技与窃取科技分支保持待验证和手动处理；外交非空
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
