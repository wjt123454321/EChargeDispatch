# B 部分充电站桩管理审查报告

## 审查人：张云飞（充电站 + 桩管理）　模块：`station/*`、`init_system`　日期：2026-06-13

---

## 结论

- [ ] 与需求一致
- [x] 存在待确认问题（见下）
- [x] 存在明确缺陷（问题 #1）

**总体说明**：View 层职责清晰，系统配置读写、桩启停主流程与 API 文档大体一致，`start_pile` 正确触发 `DispatchService.try_dispatch_all()`。存在 1 个高优先级缺陷（`power_off` 与故障待重调度判定不一致），以及若干中低优先级设计与校验问题。分工文档建议对照的三项 API 自动化测试均已通过。

---

## 问题列表

| 序号 | 文件:行号 | 现象 | 严重程度 | 建议 |
|------|-----------|------|----------|------|
| 1 | `station/services.py:141-148` | 故障桩上仍有 `pending_reschedule` 车辆时 `power_off` 返回成功 | 高 | 与 `QueueService.pile_occupancy_count` 对齐，或显式拒绝 |
| 2 | `station/services.py:128-129` | `off` 状态桩可直接 `start` 到 `available`，跳过 `standby` | 中 | 收紧前置状态为仅 `standby`，或文档明确允许 |
| 3 | `station/services.py:49-65` | `PUT` 修改 `fast_pile_num`/`slow_pile_num` 不同步实体桩 | 中 | 禁止运行时改桩数，或同步增删 `ChargingPile` |
| 4 | `station/services.py:49-65` | 可写入 0/负数等非法 N、M、桩数 | 中 | 增加 `> 0` 及合理范围校验 |
| 5 | `station/services.py:132` | 模拟时钟下 `last_heartbeat_at` 使用墙钟时间 | 中 | 改为 `system_now()` |
| 6 | `init_system.py:42-52` | 初始化后桩直接为 `available`，跳过生命周期 | 低 | 验收可接受；演示 UC 需单独场景 |
| 7 | `station/services.py:36-46` + `billing/services.py` | 配置展示 `service_price` 与计费常量可能脱节 | 低 | 与 D 模块统一服务费数据源 |
| 8 | `tests/test_all_apis.py:108` | `start` 后断言过宽，无法约束状态机 | 低 | 改为 `assertEqual(status, 'available')` |
| 9 | `station/services.py` | 桩状态变更无 `@transaction.atomic` | 低 | 评估并发场景后加事务 |

---

## 必查逻辑逐项状态

依据 [代码审查分工.md](./代码审查分工.md) 中 B 模块必查逻辑，逐项核对如下：

| # | 必查项 | 是否已审查 | 结论 | 说明 |
|---|--------|------------|------|------|
| 1 | 桩状态机：`off→standby→available↔charging`，故障 `fault` | 是 | ⚠️ 部分符合 | `PileStatus` 枚举完整；`available↔charging`、故障置 `fault` 由 D/E 模块维护，已交叉阅读确认。`start_pile` 允许 `off` 直跳 `available`（问题 #2），与架构文档两步流程不一致 |
| 2 | `power_on`：仅 `off/standby` → `standby` | 是 | ✅ 符合 | 代码逻辑与 API 行为一致 |
| 3 | `start_pile` → `available` 并触发 `try_dispatch_all()` | 是 | ✅ 符合 | 已确认调用 `DispatchService.try_dispatch_all()` |
| 4 | `power_off`：无排队票、无在充会话才可关闭 | 是 | ❌ 不符合 | 实现仅检查 active 票与会话；故障后 `pending_reschedule` 仍属桩上车辆（问题 #1），集成场景已复现 |
| 5 | `SystemConfig` 默认 N=10、M=3、2 快充 + 3 慢充 | 是 | ✅ 符合 | `models.py` 与 `init_system.py` 一致 |
| 6 | `update_config` 允许字段与枚举校验 | 是 | ⚠️ 基本符合 | 白名单及 `fault_strategy`、`dispatch_mode` 校验正确；另发现数值未校验（#4）、改桩数不同步实体桩（#3） |
| 7 | `init_system`：管理员、桩、计费策略初始化完整 | 是 | ⚠️ 基本完整 | 站点、配置、5 桩、管理员、峰平谷策略均已初始化；桩初始为 `available` 而非 `off`（问题 #6） |

---

## 问题详情：现象与原因

### 问题 #1 — `power_off` 在故障待重调度时仍可关桩（高）

**运行时现象**

- 故障上报后，若车辆未能迁到其他桩，处于 `pending_reschedule`，仍绑定在故障桩 `current_pile` 上。
- `GET /api/pile/status` 显示该桩 `queue_used > 0`；`GET /api/queue/pile/{id}` 队列明细含 `pending_reschedule`。
- `POST /api/pile/{id}/poweroff` 仍返回 **200 / code=0**，桩变为 `off`，响应中 `queue_used` 仍大于 0；DB 中请求仍为 `pending_reschedule` 且指向已关闭的桩。

**原因**

- `power_off` 仅检查 `QueueTicket(is_active=True)` 与在充 `ChargingSession`。
- 故障流程（E 模块 `report_fault`）将请求改为 `pending_reschedule` 并 deactivate 排队票，在充会话已结束。
- 展示/调度占用使用 `QueueService.pile_occupancy_count`，统计 `CHARGING`、`DISPATCHED`、`PENDING_RESCHEDULE` 三种状态。
- 关桩判定与统一占用统计不一致，导致误判「桩上无人」。

---

### 问题 #2 — `start_pile` 允许从 `off` 直接到 `available`（中）

**运行时现象**

- 对 `off` 桩直接调用 `POST /api/pile/{id}/start` 成功，桩一步变为 `available` 并触发调度，无需先 `poweron`。
- 与架构文档 `off → standby → available` 不一致；API 文档未禁止，日常使用中通常无功能错误。

**原因**

- `start_pile` 前置条件允许 `{PileStatus.STANDBY, PileStatus.OFF}`，状态机实现比设计文档更宽松。

---

### 问题 #3 — 修改配置桩数量不同步实体桩（中）

**运行时现象**

- `PUT /api/admin/system-config` 修改 `fast_pile_num`/`slow_pile_num` 后，GET 配置数字已变，但 `GET /api/pile/status` 仍只返回原有实体桩数量。
- `normal`/`single_min_total` 调度仍只使用 DB 中真实桩；`batch_min_total` 用配置桩数计算系统总容量，与实际桩数错位，可能导致批量调度过早或过晚触发。

**原因**

- `update_config` 只更新 `SystemConfig` 字段，未像 `init_system` 那样增删 `ChargingPile` 记录。
- C 模块 `_try_batch_dispatch` 用配置桩数算容量，选桩却来自 DB 查询，两处数据源不一致。

---

### 问题 #4 — `update_config` 缺少数值边界校验（中）

**运行时现象**

- 传入 `waiting_area_size: 0`、`charging_queue_len: -1` 等非法值时，接口仍可能返回 200 更新成功。
- 随后等候区满员判定、队列容量、调度行为异常，且不易联想到配置错误。

**原因**

- Service 层仅校验 `fault_strategy`、`dispatch_mode` 枚举，整数字段无 `> 0` 或范围检查；Model 层也不禁止 0/负数。

---

### 问题 #5 — `start_pile` 使用 `timezone.now()` 而非 `system_now()`（中）

**运行时现象**

- 开启模拟时钟（验收/快照测试）时，其他业务时间按模拟时间推进，但 `last_heartbeat_at` 写入真实墙钟时间，与业务时间轴不一致。
- 当前 `last_heartbeat_at` 基本不参与调度/计费，日常接口测试几乎无感。

**原因**

- `station` 模块未引入 `system_now()`，直接使用 Django 默认 `timezone.now()`，违反项目统一时间源约定（联审清单 #2）。

---

### 问题 #6 — `init_system` 初始化桩直接为 `available`（低）

**运行时现象**

- 执行 `init_system` 后，5 根桩已是 `available` 且 `is_enabled=True`，用户可立即提交充电请求，无需管理员逐桩启桩。
- 与完整 UC「先启桩再充电」演示路径不一致；对测试与验收通常是便利行为。

**原因**

- 初始化命令优先考虑开箱即用，未模拟 `off → standby → start` 生命周期。

---

### 问题 #7 — `service_price` 展示与计费双源（低）

**运行时现象**

- 默认配置下 GET 配置与账单服务费均为 0.8 元/度，表现一致。
- 若修改 DB 中 `SystemConfig.service_price` 或 `TariffPolicy.service_price`，配置页可能显示新值，但计费仍用枚举常量 `SERVICE_FEE_RATE=0.8`；PUT 接口不可改 `service_price`。

**原因**

- 存在三处「0.8」定义（`SystemConfig`、`TariffPolicy`、枚举常量），计费只读枚举，展示读 DB，未打通。

---

### 问题 #8 — 测试断言过宽（低）

**运行时现象**

- 无线上/手工运行现象，仅影响自动化测试：`test_admin_pile_lifecycle` 在 `start` 后接受 `available` 或 `standby`，无法作为状态机回归保护。

**原因**

- 测试编写时放宽断言条件，无法发现 #2 类偏差。

---

### 问题 #9 — 桩状态变更缺少事务包裹（低）

**运行时现象**

- 单用户顺序操作几乎遇不到；高并发下 `start_pile` 与调度同时发生时，可能出现桩状态与队列短暂不一致。

**原因**

- `power_on`/`start_pile`/`power_off` 无 `@transaction.atomic`，而 `start_pile` 内调用 `try_dispatch_all()` 涉及多表写入。

---

## 问题 #1 集成场景验证

按审查分工中「故障 + 等候区」交叉点思路，通过 API 手工/集成场景复现问题 #1：

### 场景步骤

```text
1. init_system
2. 管理员关闭 F2（仅保留 F1 为唯一可用快充桩）
3. 两名用户各提交快充请求 → 派至 F1 队列
4. POST /api/admin/fault/report { pile_id: F1 }
5. 确认 F1 上存在 pending_reschedule 车辆
6. GET /api/pile/status、GET /api/queue/pile/{F1} 确认 queue_used > 0
7. POST /api/pile/{F1}/poweroff → 记录实际响应
```

### 故障上报后（关桩前）

| 检查项 | 结果 |
|--------|------|
| F1.status | `fault` |
| pending_reschedule 车辆数 | 2 |
| `GET /api/pile/status` → F1.queue_used | 2 |
| `GET /api/queue/pile/{F1}` | 队列含 `pending_reschedule` |

### 执行 power_off 后

| 检查项 | 期望 | 实际 |
|--------|------|------|
| 业务 code | **4002** | **0（success）** |
| F1.status | 保持 `fault` | **`off`** |
| 响应 queue_used | — | **仍为 2** |
| DB 中 pending 请求 | 仍绑定 F1 | **2 条**，`current_pile.status=off` |

### 验证结论

缺陷已复现：`queue_used > 0` 时 `power_off` 仍成功，与 API 文档「桩上无排队车辆才可关闭」不符，并产生绑定在已关闭桩上的待重调度请求。

---

## 需其他模块确认

| 交叉点 | 涉及 | B 侧待确认 |
|--------|------|------------|
| 队列计数 | B/C | `power_off` 是否应与 `pile_occupancy_count` 统一；修复方案需 C 确认 |
| 故障 + 关桩 | B/E | 故障桩是否允许 `power_off`；`pending_reschedule` 存在时是否必须拒绝 |
| 时间源 | A/B | `start_pile` 心跳是否改为 `system_now()` |
| 调度触发 | B/C/D/E | `power_off` 关空桩是否需调用 `try_dispatch_all()`（当前未调用） |
| 服务费 | B/D | `SystemConfig.service_price` 是否应对齐计费实现 |

---

## 已跑测试

- [x] `test_admin_system_config` — PASS
- [x] `test_admin_pile_status` — PASS
- [x] `test_admin_pile_lifecycle` — PASS
- [ ] `test_acceptance_snapshot` — 未跑（E 模块专项）
- [ ] `run_acceptance --fast --until 09:30` — 未跑（E 模块专项）

```bash
python manage.py test apps.tests.test_all_apis.AllAPITestCase.test_admin_system_config apps.tests.test_all_apis.AllAPITestCase.test_admin_pile_status apps.tests.test_all_apis.AllAPITestCase.test_admin_pile_lifecycle --settings=config.settings.test
```

---

## 审查范围

**负责文件**

```text
backend/apps/station/
  models.py, services.py, views.py, urls.py
  management/commands/init_system.py
```

**参考文档**

- [代码审查分工.md](./代码审查分工.md)
- [智能充电桩调度计费系统详细需求.md](./智能充电桩调度计费系统详细需求.md)
- [API接口文档.md](./API接口文档.md)
- [后端架构参考手册.md](./后端架构参考手册.md)
- [后端代码审查汇总.md](./后端代码审查汇总.md)

---

## 建议后续行动

1. **优先修复问题 #1**：`power_off` 使用与 `pile_occupancy_count` 一致的占用判定。
2. **第 2 轮联审**：与 C/E 确认故障桩关桩边界与队列计数一致性。
3. **修复后回归**：重跑分工文档建议的三项 API 测试及第 4 轮全员全量测试。
