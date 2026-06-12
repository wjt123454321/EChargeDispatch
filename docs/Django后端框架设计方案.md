# 基于 Django 的后端框架设计方案

## 1. 文档目的

本文档基于现有课程作业文档与接口草稿，对智能充电桩调度计费系统给出一套适合 Django 开发的后端框架设计方案。

本文档重点回答以下问题：

- 后端推荐拆分为哪些 Django app
- 每个 app 负责哪些领域对象
- 每个 app 中的核心 model 应如何设计
- 主要接口应落在哪些 app 中

本文档定位为课程作业阶段的设计方案，强调结构清晰、领域边界明确、便于实现，不追求高并发、高可用、复杂分布式架构等生产级要求。

## 2. 设计依据

本方案综合参考以下已有材料：

- 智能充电桩调度计费系统详细需求
- 充电站系统领域模型与用例模型
- 充电站系统面向对象软件设计
- 联合验收对接开发标准
- 当前 OpenAPI 草稿接口定义

从这些文档中可以提炼出较稳定的核心业务域：

- 账号与车辆
- 充电站与充电桩
- 充电请求、排队、充电会话与调度
- 计费规则、详单与账单
- 故障处理、统计报表与管理操作

## 3. 总体设计原则

### 3.1 按核心领域拆分 app

本系统不建议完全按照接口 URL 机械拆分 app，而应优先按照稳定的业务领域边界拆分。  
这样可以避免后续模型分散、职责重复、服务层交叉依赖过多的问题。

### 3.2 保持 Django 单体项目结构

课程作业阶段采用 Django 单体应用即可，不需要额外拆成微服务。推荐在一个 Django project 下，通过多个业务 app 组织领域模型和服务逻辑。

### 3.3 模型归属优先于接口归属

app 的边界首先由“谁拥有业务事实”决定，而不是由“哪个接口调用它”决定。  
例如：

- 用户和车辆属于账号域
- 充电桩和系统配置属于站点域
- 充电请求和排队过程属于充电域
- 详单和账单属于计费域
- 故障和报表属于运维域

### 3.4 适度抽象，避免过度设计

本方案保留对课程答辩和系统说明有帮助的核心实体，但不会为了形式完整而设计过多中间表或复杂基础设施。

## 4. 推荐 app 划分

推荐将后端划分为以下 6 个 app：

- `accounts`
- `station`
- `charging`
- `billing`
- `operations`
- `common`

推荐目录结构如下：

```text
backend/
├── manage.py
├── config/
│   ├── settings/
│   ├── urls.py
│   └── wsgi.py
└── apps/
    ├── accounts/
    ├── station/
    ├── charging/
    ├── billing/
    ├── operations/
    └── common/
```

各 app 的职责如下。

### 4.1 `accounts`

负责账号与车辆基础信息管理。

主要职责：

- 用户注册与登录
- 管理员登录
- 用户与车辆关联管理
- 车辆当前状态维护

### 4.2 `station`

负责充电站基础设施与站点参数。

主要职责：

- 充电站基本信息
- 系统参数配置
- 充电桩信息与桩状态管理
- 充电桩启停控制相关基础数据

### 4.3 `charging`

负责充电业务主流程，是系统的核心业务 app。

主要职责：

- 提交与修改充电请求
- 排队号与队列位置管理
- 等候区与充电区队列流转
- 开始充电、结束充电、取消充电
- 普通调度与重调度基础记录

### 4.4 `billing`

负责费用规则与结算结果。

主要职责：

- 峰平谷计费规则配置
- 充电详单生成
- 账单生成与支付状态记录

### 4.5 `operations`

负责管理员视角下的故障、报表和日志。

主要职责：

- 故障上报与故障恢复
- 重调度结果记录
- 统计报表生成
- 管理员操作日志

### 4.6 `common`

负责公共基础能力，不承载业务主数据。

主要职责：

- 公共基类
- 枚举
- 统一响应结构
- 自定义异常
- 工具函数

## 5. 空间与状态语义

### 5.1 充电站空间划分

根据需求文档，充电站被划分为：

- 等候区
- 充电区

充电区中的每个充电桩前都存在固定位置的排队区。

因此，本系统中的排队过程不是单一队列，而是一个“等候区 -> 充电区桩前队列 -> 正在充电”的状态流转过程。

### 5.2 充电请求状态定义

`ChargingRequest.status` 推荐统一使用以下枚举值：

- `waiting`
- `queuing`
- `charging`
- `pending_reschedule`
- `completed`
- `cancelled`

其语义定义如下：

- `waiting`：车辆提交充电请求后，进入等候区，但尚未被调度进入充电区
- `queuing`：车辆已经进入充电区，但仍在某个充电桩前排队区等待
- `charging`：车辆已开始在充电桩充电
- `pending_reschedule`：由于故障等原因，正在等待重新调度
- `completed`：充电完成，已完成本次业务流程
- `cancelled`：用户主动取消或系统终止本次请求

该定义必须在实现中保持一致，否则会导致接口语义与界面展示混乱。

## 6. 各 app 的 model 设计

## 6.1 `accounts` app

### 6.1.1 设计目标

`accounts` 负责系统中的“人”和“车”。

其中：

- 用户是发起充电请求的主体
- 管理员是执行运维操作的主体
- 车辆是被充电请求所指向的业务对象

### 6.1.2 推荐模型

- `UserAccount`
- `AdminAccount`
- `Vehicle`

### 6.1.3 `UserAccount`

表示普通用户账号。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `user_name` | CharField | 用户名 |
| `password_hash` | CharField | 密码哈希 |
| `is_active` | BooleanField | 是否启用 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

说明：

- 课程作业阶段可以不扩展手机号、邮箱等复杂资料字段
- 若后续实现想更贴近 Django，可基于自定义用户模型扩展

### 6.1.4 `AdminAccount`

表示管理员账号。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `admin_code` | CharField | 管理员编号 |
| `user_name` | CharField | 登录名 |
| `password_hash` | CharField | 密码哈希 |
| `is_active` | BooleanField | 是否启用 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

说明：

- 管理员可以与普通用户分表设计，课程实现更清晰
- 若后续想合并为统一用户表，也可用 `role` 区分

### 6.1.5 `Vehicle`

表示用户拥有的车辆。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `user` | ForeignKey(UserAccount) | 所属用户 |
| `plate_no` | CharField | 车牌号，建议唯一 |
| `battery_capacity` | DecimalField | 物理电池容量 |
| `current_battery_level` | DecimalField | 当前剩余电量 |
| `is_charging` | BooleanField | 是否正在充电 |
| `vehicle_status` | CharField | 车辆当前状态 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

说明：

- `battery_capacity` 对应车辆物理电池容量
- `current_battery_level` 表示当前剩余电量
- `is_charging` 便于前后端快速判断
- `vehicle_status` 推荐取值：`idle`、`waiting`、`queuing`、`charging`

推荐关系：

- 一个 `UserAccount` 可以拥有多辆 `Vehicle`
- 一辆 `Vehicle` 可以关联多次历史 `ChargingRequest`

## 6.2 `station` app

### 6.2.1 设计目标

`station` 负责表达“充电站有什么设施、当前参数是什么”。

### 6.2.2 推荐模型

- `ChargingStation`
- `SystemConfig`
- `ChargingPile`

### 6.2.3 `ChargingStation`

表示充电站本体。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `station_code` | CharField | 站点编号 |
| `station_name` | CharField | 站点名称 |
| `status` | CharField | 站点状态 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

说明：

- 课程作业通常只有一个站点，但保留站点实体更便于设计完整性

### 6.2.4 `SystemConfig`

表示系统运行参数配置。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `station` | ForeignKey(ChargingStation) | 所属站点 |
| `fast_pile_num` | IntegerField | 快充桩数量 |
| `slow_pile_num` | IntegerField | 慢充桩数量 |
| `waiting_area_size` | IntegerField | 等候区容量 |
| `charging_queue_len` | IntegerField | 每个充电桩前排队区长度 |
| `fault_strategy` | CharField | 故障调度策略 |
| `dispatch_mode` | CharField | 普通调度模式 |
| `service_price` | DecimalField | 服务费单价 |
| `is_active` | BooleanField | 是否当前生效 |
| `effective_from` | DateTimeField | 生效时间 |
| `created_at` | DateTimeField | 创建时间 |

说明：

- 该模型对接 `/api/admin/system-config`
- 推荐取值：
  - `fault_strategy`: `priority` / `time_order`
  - `dispatch_mode`: `normal` / `single_min_total` / `batch_min_total`

### 6.2.5 `ChargingPile`

表示具体充电桩。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `station` | ForeignKey(ChargingStation) | 所属站点 |
| `pile_no` | CharField | 桩编号 |
| `pile_type` | CharField | `F` 或 `T` |
| `rated_power` | DecimalField | 额定功率 |
| `status` | CharField | 桩状态 |
| `is_enabled` | BooleanField | 是否启用 |
| `current_queue_length` | IntegerField | 当前队列长度 |
| `total_charge_num` | IntegerField | 累计充电次数 |
| `total_charge_time` | DecimalField | 累计充电时长 |
| `total_charge_capacity` | DecimalField | 累计充电量 |
| `last_heartbeat_at` | DateTimeField | 最近心跳时间 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

说明：

- `status` 推荐值：`off`、`standby`、`available`、`charging`、`fault`
- 累计统计字段保存在桩表中，便于管理员端查询

## 6.3 `charging` app

### 6.3.1 设计目标

`charging` 是系统业务核心，负责请求、排队、调度和会话。

### 6.3.2 推荐模型

- `ChargingRequest`
- `QueueTicket`
- `ChargingSession`
- `DispatchRecord`

### 6.3.3 `ChargingRequest`

表示一次充电请求，是本系统最核心的业务实体之一。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `request_no` | CharField | 请求编号 |
| `user` | ForeignKey(UserAccount) | 发起用户 |
| `vehicle` | ForeignKey(Vehicle) | 对应车辆 |
| `request_mode` | CharField | 快充或慢充 |
| `request_amount` | DecimalField | 请求充电量 |
| `status` | CharField | 请求状态 |
| `request_time` | DateTimeField | 提交时间 |
| `queued_at` | DateTimeField | 进入排队体系时间 |
| `charge_started_at` | DateTimeField | 开始充电时间 |
| `charge_ended_at` | DateTimeField | 结束充电时间 |
| `current_pile` | ForeignKey(ChargingPile, null=True) | 当前所属桩 |
| `remark` | TextField | 备注 |

说明：

- `user` 和 `vehicle` 都建议保留
- 一个 `Vehicle` 在同一时刻只能存在一个未完成的 `ChargingRequest`
- 修改充电模式时不建议创建新请求，而是在原请求上更新模式并重新排队

### 6.3.4 `QueueTicket`

表示充电请求在某个队列中的排队凭据。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `request` | ForeignKey(ChargingRequest) | 对应请求 |
| `queue_num` | CharField | 排队号码，如 `F1`、`T2` |
| `queue_type` | CharField | 队列类型 |
| `pile` | ForeignKey(ChargingPile, null=True) | 对应充电桩 |
| `queue_position` | IntegerField | 队列位置 |
| `entered_queue_at` | DateTimeField | 进入该队列时间 |
| `is_active` | BooleanField | 是否当前有效 |

建议 `queue_type` 含义：

- `waiting_area`：等候区
- `pile_queue`：充电区中具体充电桩前排队区

说明：

- 当 `queue_type = waiting_area` 时，`pile` 可以为空
- 当 `queue_type = pile_queue` 时，`pile` 不应为空
- 一个 `ChargingRequest` 在任一时刻应只有一个有效 `QueueTicket`

### 6.3.5 `ChargingSession`

表示车辆真正开始充电后的会话。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `session_no` | CharField | 会话编号 |
| `request` | OneToOneField / ForeignKey | 来源请求 |
| `vehicle` | ForeignKey(Vehicle) | 对应车辆 |
| `pile` | ForeignKey(ChargingPile) | 充电桩 |
| `start_time` | DateTimeField | 开始时间 |
| `end_time` | DateTimeField | 结束时间 |
| `charged_amount` | DecimalField | 实际充电量 |
| `charged_duration` | DecimalField | 充电时长 |
| `session_status` | CharField | 会话状态 |
| `stop_reason` | CharField | 停止原因 |
| `created_at` | DateTimeField | 创建时间 |

说明：

- `ChargingSession` 在开始充电时创建
- 正常结束、取消中断、故障中断都应在此表体现

### 6.3.6 `DispatchRecord`

表示一次调度行为的过程记录。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `request` | ForeignKey(ChargingRequest) | 被调度请求 |
| `source_type` | CharField | 来源位置 |
| `target_pile` | ForeignKey(ChargingPile, null=True) | 目标桩 |
| `dispatch_strategy` | CharField | 调度策略 |
| `before_status` | CharField | 调度前状态 |
| `after_status` | CharField | 调度后状态 |
| `dispatched_at` | DateTimeField | 调度时间 |
| `operator_type` | CharField | 系统或管理员 |

说明：

- 该表不是绝对必须，但建议保留
- 对课程答辩、调试、故障分析都很有帮助

## 6.4 `billing` app

### 6.4.1 设计目标

`billing` 负责计费规则与结算结果。

### 6.4.2 推荐模型

- `TariffPolicy`
- `TariffPeriod`
- `ChargeDetail`
- `Bill`

### 6.4.3 `TariffPolicy`

表示一套计费策略。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `policy_name` | CharField | 策略名称 |
| `service_price` | DecimalField | 服务费单价 |
| `is_active` | BooleanField | 是否当前生效 |
| `effective_from` | DateTimeField | 生效时间 |
| `created_at` | DateTimeField | 创建时间 |

### 6.4.4 `TariffPeriod`

表示策略中的时段价格。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `policy` | ForeignKey(TariffPolicy) | 所属策略 |
| `period_type` | CharField | 峰/平/谷 |
| `start_time` | TimeField | 开始时间 |
| `end_time` | TimeField | 结束时间 |
| `unit_price` | DecimalField | 单位电价 |

说明：

- `TariffPolicy + TariffPeriod` 可以较自然地表达峰平谷计费
- 也便于后续扩展跨时段拆分计费

### 6.4.5 `ChargeDetail`

表示单次充电生成的详单。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `detail_no` | CharField | 详单编号 |
| `session` | OneToOneField(ChargingSession) | 对应会话 |
| `request` | ForeignKey(ChargingRequest) | 对应请求 |
| `vehicle` | ForeignKey(Vehicle) | 对应车辆 |
| `pile` | ForeignKey(ChargingPile) | 对应充电桩 |
| `tariff_policy` | ForeignKey(TariffPolicy) | 使用策略 |
| `charge_amount` | DecimalField | 充电量 |
| `charge_duration` | DecimalField | 充电时长 |
| `start_time` | DateTimeField | 开始时间 |
| `end_time` | DateTimeField | 结束时间 |
| `charge_fee` | DecimalField | 充电费 |
| `service_fee` | DecimalField | 服务费 |
| `total_fee` | DecimalField | 总费用 |
| `generated_at` | DateTimeField | 生成时间 |

### 6.4.6 `Bill`

表示账单对象。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `bill_no` | CharField | 账单编号 |
| `user` | ForeignKey(UserAccount) | 所属用户 |
| `bill_date` | DateField | 账单日期 |
| `total_charge_amount` | DecimalField | 总充电量 |
| `total_charge_duration` | DecimalField | 总时长 |
| `total_charge_fee` | DecimalField | 总充电费 |
| `total_service_fee` | DecimalField | 总服务费 |
| `total_fee` | DecimalField | 总费用 |
| `pay_status` | CharField | 支付状态 |
| `paid_at` | DateTimeField | 支付时间 |
| `created_at` | DateTimeField | 创建时间 |

说明：

- 课程作业可先简化为“一次详单对应一张账单”
- 后续若要扩展为按日汇总账单，也可在此基础上调整

## 6.5 `operations` app

### 6.5.1 设计目标

`operations` 负责管理员运维视角下的故障、报表与日志。

### 6.5.2 推荐模型

- `FaultRecord`
- `RescheduleRecord`
- `OperationLog`
- `ReportSnapshot`

### 6.5.3 `FaultRecord`

表示一次充电桩故障事件。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `pile` | ForeignKey(ChargingPile) | 故障桩 |
| `fault_type` | CharField | 故障类型 |
| `fault_status` | CharField | `open/recovered` |
| `occurred_at` | DateTimeField | 故障发生时间 |
| `recovered_at` | DateTimeField | 恢复时间 |
| `description` | TextField | 故障说明 |

### 6.5.4 `RescheduleRecord`

表示故障或恢复后某一辆车的重调度结果。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `fault_record` | ForeignKey(FaultRecord) | 对应故障记录 |
| `request` | ForeignKey(ChargingRequest) | 对应请求 |
| `source_pile` | ForeignKey(ChargingPile, null=True) | 原桩 |
| `target_pile` | ForeignKey(ChargingPile, null=True) | 新桩 |
| `strategy_type` | CharField | 调度策略 |
| `result_status` | CharField | 调度结果 |
| `handled_at` | DateTimeField | 处理时间 |

### 6.5.5 `OperationLog`

表示管理员操作日志。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `admin` | ForeignKey(AdminAccount) | 操作管理员 |
| `operation_type` | CharField | 操作类型 |
| `target_type` | CharField | 操作对象类型 |
| `target_id` | CharField | 操作对象标识 |
| `content` | TextField | 操作内容 |
| `created_at` | DateTimeField | 操作时间 |

### 6.5.6 `ReportSnapshot`

表示报表快照。

建议字段：

| 字段名 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | BigAutoField / UUID | 主键 |
| `period_type` | CharField | 日/周/月 |
| `report_date` | DateField | 报表日期 |
| `pile` | ForeignKey(ChargingPile) | 统计对象桩 |
| `total_charge_num` | IntegerField | 累计充电次数 |
| `total_charge_time` | DecimalField | 累计充电时长 |
| `total_charge_capacity` | DecimalField | 累计充电量 |
| `total_charge_fee` | DecimalField | 累计充电费 |
| `total_service_fee` | DecimalField | 累计服务费 |
| `total_fee` | DecimalField | 累计总费用 |
| `generated_at` | DateTimeField | 生成时间 |

说明：

- 课程作业阶段采用快照表生成报表，简单直接
- 也便于管理员端反复查询

## 6.6 `common` app

### 6.6.1 设计目标

`common` 只提供基础能力，不放核心业务实体。

### 6.6.2 推荐内容

- `BaseModel`
- 枚举定义
- 统一响应结构
- 自定义异常
- 时间与金额处理工具

说明：

- 不建议把 `common` 做成“杂项业务表容器”
- 业务数据应尽量归属到明确领域 app 中

## 7. 关键关系设计

推荐核心关系如下：

```text
UserAccount 1 ---- n Vehicle
UserAccount 1 ---- n ChargingRequest
Vehicle 1 ---- n ChargingRequest
ChargingRequest 1 ---- n QueueTicket
ChargingRequest 1 ---- 0..1 ChargingSession
ChargingPile 1 ---- n QueueTicket
ChargingPile 1 ---- n ChargingSession
ChargingSession 1 ---- 0..1 ChargeDetail
Bill 1 ---- 1..n ChargeDetail
ChargingPile 1 ---- n FaultRecord
FaultRecord 1 ---- n RescheduleRecord
AdminAccount 1 ---- n OperationLog
TariffPolicy 1 ---- n TariffPeriod
```

## 8. Service 设计建议

虽然本文档重点放在 app 和 model，但为了保证后续实现结构清晰，建议各 app 同时设计对应 service。

### 8.1 `accounts.services`

- `AuthService`
- `VehicleService`

职责：

- 注册
- 登录
- 密码校验
- 车辆创建
- 车辆状态同步

### 8.2 `station.services`

- `StationConfigService`
- `ChargingPileService`

职责：

- 查询和修改系统参数
- 启动充电桩
- 投入运行
- 关闭充电桩
- 查询桩状态

### 8.3 `charging.services`

- `ChargingRequestService`
- `QueueService`
- `DispatchService`
- `ChargingSessionService`

职责：

- 提交充电请求
- 修改请求电量
- 修改请求模式
- 查询排队状态
- 开始充电
- 查询充电状态
- 结束充电
- 取消充电
- 普通调度与扩展调度

### 8.4 `billing.services`

- `TariffService`
- `BillingService`

职责：

- 电价时段计算
- 服务费计算
- 生成详单
- 生成账单
- 更新支付状态

### 8.5 `operations.services`

- `FaultService`
- `RescheduleService`
- `ReportService`
- `OperationLogService`

职责：

- 故障上报
- 故障恢复
- 优先级调度
- 时间顺序调度
- 统计报表生成
- 管理员操作记录

## 9. 接口与 app 的对应关系

### 9.1 认证接口

- `/api/auth/register` -> `accounts`
- `/api/auth/login` -> `accounts`

### 9.2 用户充电接口

- `/api/charging/request` -> `charging`
- `/api/charging/amount` -> `charging`
- `/api/charging/mode` -> `charging`
- `/api/charging/queue-status` -> `charging`
- `/api/charging/start` -> `charging`
- `/api/charging/status` -> `charging`
- `/api/charging/end` -> `charging`
- `/api/charging/cancel` -> `charging`

### 9.3 账单接口

- `/api/bill/list` -> `billing`
- `/api/bill/detail/{bill_id}` -> `billing`
- `/api/bill/pay/{bill_id}` -> `billing`

### 9.4 站点与充电桩接口

- `/api/admin/system-config` -> `station`
- `/api/pile/status` -> `station`
- `/api/queue/pile/{pile_id}` -> `charging`
- `/api/pile/{pile_id}/poweron` -> `station`
- `/api/pile/{pile_id}/start` -> `station`
- `/api/pile/{pile_id}/poweroff` -> `station`

### 9.5 运维接口

- `/api/admin/fault/report` -> `operations`
- `/api/admin/fault/recover` -> `operations`
- `/api/admin/fault/list` -> `operations`
- `/api/admin/report/stats` -> `operations`

### 9.6 外部接口处理建议

当前不单独设计 `integration` app。  
`/api/v1/external/*` 只作为外部适配入口，底层复用已有 app 的服务与模型：

- 认证能力复用 `accounts`
- 站点状态复用 `station`
- 提交和查询充电请求复用 `charging`

## 10. 实现约束建议

为避免后续编码阶段状态错乱，建议固定以下约束：

- 一个 `Vehicle` 在同一时刻只能有一个未完成的充电请求
- 一个 `ChargingRequest` 在同一时刻只能有一个有效 `QueueTicket`
- `Vehicle.is_charging`、`Vehicle.vehicle_status`、`ChargingRequest.status`、`ChargingSession.session_status` 应通过事务同步更新
- 修改充电量时，不改变排队号
- 修改充电模式时，重新生成排队号，并重新进入目标模式队列末尾
- 用户从等候区进入充电区时，不重新创建请求，只更新状态和队列信息
- 故障发生时，受影响请求进入 `pending_reschedule`
- 结束充电和取消充电后，应生成详单，再更新账单与支付状态

## 11. 方案结论

综合现有需求文档、接口草稿和课程作业场景，本系统推荐采用如下后端结构：

- `accounts`：用户、管理员、车辆
- `station`：充电站、系统参数、充电桩
- `charging`：充电请求、排队号、充电会话、调度记录
- `billing`：计费策略、时段价格、详单、账单
- `operations`：故障记录、重调度记录、操作日志、报表快照
- `common`：基础抽象与公共能力

其中，`Vehicle` 独立建表、`ChargingRequest` 显式关联车辆、并明确区分 `waiting` 与 `queuing` 的空间语义，是本方案中最关键的建模决策。  
这一设计既能贴合你们现有文档中的领域模型，也足够支撑 Django 课程作业阶段的后续编码实现。
