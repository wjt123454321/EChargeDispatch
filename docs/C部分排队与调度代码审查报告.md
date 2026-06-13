# C 部分排队与调度代码审查报告

## 1. 审查范围

本文档针对 [代码审查分工.md:L83-L113](file:///d:/EChargeDispatch_backend/EChargeDispatch/docs/%E4%BB%A3%E7%A0%81%E5%AE%A1%E6%9F%A5%E5%88%86%E5%B7%A5.md#L83-L113) 中 C 部分指定范围，基于当前实际代码重新进行分析、说明与解释。

本次审查重点覆盖：

- [models.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/models.py)
- [services.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py)
- [views.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/views.py)
- [urls.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/urls.py)
- [test_single_dispatch_strategy.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_single_dispatch_strategy.py)
- [test_batch_dispatch_strategy.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_batch_dispatch_strategy.py)
- [test_batch_dispatch_command.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_batch_dispatch_command.py)
- [test_acceptance_snapshot.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_acceptance_snapshot.py)
- [test_all_apis.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_all_apis.py)

同时结合以下文档进行交叉核对：

- [智能充电桩调度计费系统详细需求.md](file:///d:/EChargeDispatch_backend/EChargeDispatch/docs/%E6%99%BA%E8%83%BD%E5%85%85%E7%94%B5%E6%A1%A9%E8%B0%83%E5%BA%A6%E8%AE%A1%E8%B4%B9%E7%B3%BB%E7%BB%9F%E8%AF%A6%E7%BB%86%E9%9C%80%E6%B1%82.md)
- [Django后端框架设计方案.md](file:///d:/EChargeDispatch_backend/EChargeDispatch/docs/Django%E5%90%8E%E7%AB%AF%E6%A1%86%E6%9E%B6%E8%AE%BE%E8%AE%A1%E6%96%B9%E6%A1%88.md)
- [README.md](file:///d:/EChargeDispatch_backend/EChargeDispatch/README.md)

## 2. 审查结论

当前版本的 C 部分实现，已经能够较完整地支撑“提交请求 -> 等候区排队 -> 进入充电区桩前队列 -> 开始充电 -> 结束/取消 -> 再调度”的主业务链路，并且扩展调度部分相较此前版本已经有明显完善。

本次重新审查后的结论如下：

- `ChargingRequest`、`QueueTicket`、`DispatchRecord` 的建模结构清晰，能够支撑排队、调度、留痕与展示
- 视图层采用“薄控制器 + 服务层承载规则”的设计，接口边界清楚
- `QueueService` 与 `DispatchService` 的职责划分合理：前者处理排队位置和票据，后者处理调度与派桩
- `normal` 模式已经实现“FIFO + 同模式下最短完成时间选桩”
- `single_min_total` 已不再是简单贪心，而是对本轮候选集合进行带剪枝的精确最优分配
- `batch_min_total` 已不再是滚动贪心，而是严格批次门控下的整批精确分配算法
- 命令级演示 `run_single_dispatch` / `run_batch_dispatch` 已可直接调用真实算法进行展示

当前仍然保留的主要差异点只有 1 项：

- 在 `batch_min_total` 语义下，题目文本要求“客户请求只需要指定充电量大小”，但当前 API 和模型入口仍然保留 `request_mode` 作为必填输入，并继续生成 `F/T` 排队号。这意味着调度核心已经支持“忽略模式分配”，但输入层尚未完全改造成“只填充电量”的形态。

## 3. 当前关键发现

| No. | 问题标题 | 结论 | 影响 |
| --- | --- | --- | --- |
| 1 | `batch_min_total` 的输入层仍保留 `request_mode` | 中优先级设计偏差 | 不影响当前批量调度算法求解，但与题目“客户仅指定充电量”的表述仍不完全一致 |

### 3.1 发现一：批量调度的核心算法已到位，但输入层仍保留模式语义

当前批量调度的核心行为已经是：

- 忽略快慢模式
- 允许任意请求分配任意启用充电桩
- 在严格批次门控下，对一整批车辆做总完成时长最短分配

对应代码位于 [DispatchService._try_batch_dispatch](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L447-L465) 和 [DispatchService._build_batch_min_total_plan](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L215-L261)。

但请求入口 [ChargingRequestService.submit_request](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L504-L554) 仍然要求：

- `request_mode` 必须是 `F/T`
- 排队号仍通过 [QueueService.next_queue_num](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L68-L78) 生成 `F{n}` / `T{n}`
- `ChargingRequest.request_mode` 仍是持久字段，见 [ChargingRequest](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/models.py#L8-L23)

因此，当前状态更准确的表述应为：

- 调度核心：已经支持“批量模式下忽略申请模式求解”
- 输入接口：仍然沿用普通模式时代的 `F/T + queue_num` 输入语义

这不会破坏算法正确性，但会造成“题目要求”和“接口输入形式”之间仍存在一层映射成本。

## 4. 模型字段设计分析

### 4.1 `ChargingRequest`

[ChargingRequest](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/models.py#L8-L27) 是整个 C 部分的核心过程实体，字段设计如下：

- `request_no`：请求业务号，便于对外展示与追踪
- `user`：发起请求的用户
- `vehicle`：本次请求对应的车辆
- `request_mode`：申请时的快充/慢充模式
- `request_amount`：请求充电量
- `status`：请求状态，当前使用 `queuing / dispatched / charging / pending_reschedule / completed / cancelled`
- `request_time`：请求创建时间，也是普通调度和单次调度中 FIFO 的基础字段
- `queued_at`：进入当前排队阶段的时间戳，既用于前端位置展示，也用于桩前队列顺序控制
- `charge_started_at / charge_ended_at`：真实充电起止时间
- `current_pile`：当前归属桩，处于等候区时为空，进入充电区后指向目标桩
- `queue_num`：排队号，普通/单次模式下体现 `F/T` 前缀规则
- `remark`：预留扩展字段

该模型的优点是：

- 用户、车辆、调度、会话之间的关系都能从 `ChargingRequest` 出发串联起来
- 时间字段足以支撑 FIFO、位置展示、计费与统计
- `current_pile + status` 的组合足以表达“等候区 / 桩前队列 / 正在充电 / 故障待重调度”这几类核心状态

### 4.2 `QueueTicket`

[QueueTicket](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/models.py#L29-L40) 是“排队位置”的持久化表达，关键字段包括：

- `request`：票据所属请求
- `queue_num`：对外展示编号
- `queue_type`：`waiting_area` 或 `pile_queue`
- `pile`：仅在桩前队列票据中存在
- `queue_position`：当前队列位次
- `entered_queue_at`：进入该队列的时间
- `is_active`：当前票据是否有效

该建模方案的价值在于：

- 不需要额外引入 `Queue` 主实体，也能表达多类队列
- 等候区与桩前排队区共用同一套数据结构，便于统一处理
- 位次和时间戳可为前端与调试输出提供稳定依据

### 4.3 `ChargingSession`

虽然分工单中 C 部分重点列的是 `ChargingRequest / QueueTicket / DispatchRecord`，但 [ChargingSession](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/models.py#L43-L58) 实际上是调度估时的重要依赖：

- `DispatchService._estimate_pile_completion_time()` 会读取某桩当前激活中的 session
- `start_charging()` / `end_charging()` 通过该模型承接“从排队到真正开始充电”的边界

字段上主要承担：

- 会话唯一号 `session_no`
- 一次请求对应一次会话 `request`
- 实际服务桩 `pile`
- `start_time / end_time`
- `charged_amount / charged_duration`
- `session_status / stop_reason`

### 4.4 `DispatchRecord`

[DispatchRecord](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/models.py#L60-L71) 的字段设计用于表达一次派桩留痕：

- `request`
- `source_type`
- `target_pile`
- `dispatch_strategy`
- `before_status / after_status`
- `dispatched_at`
- `operator_type`

它不是流程必需的状态表，但对以下场景很重要：

- 解释某辆车为什么从等候区被调到某个桩
- 分析扩展调度策略的实际分配结果
- 为答辩或日志排障提供证据链

## 5. 视图与接口设计分析

### 5.1 设计风格

[views.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/views.py) 采用的是典型的“薄控制器”风格：

- 通过装饰器完成鉴权：`@require_user` / `@require_admin`
- 通过 `parse_json_body()` 解析请求参数
- 视图函数本身只负责：取当前车辆、调用服务层、包装统一响应
- 业务规则全部下沉到 `ChargingRequestService` / `ChargingSessionService`

这种设计的优点是：

- 控制器代码短、职责清晰
- 复杂校验和状态流转不会散落在视图层
- 测试时可同时覆盖“服务级测试”和“API 级测试”

### 5.2 主要接口

[urls.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/urls.py#L5-L15) 暴露了以下核心接口：

- `POST /charging/request`：提交充电请求
- `PUT /charging/amount`：修改充电量
- `PUT /charging/mode`：修改充电模式
- `GET /charging/queue-status`：查询排队状态
- `POST /charging/start`：开始充电
- `GET /charging/status`：查询充电状态
- `POST /charging/end`：结束充电
- `DELETE /charging/cancel`：取消充电
- `GET /queue/pile/<pile_id>`：管理员查看桩队列明细

### 5.3 视图层与服务层的边界

可以看出，当前设计不是 DRF ViewSet 风格，而是手工函数式 API：

- 用户侧接口：主要围绕“我的车辆当前请求 / 当前会话”展开
- 管理员侧接口：主要提供桩队列可视化输出
- 真正决定排队、派桩、估时、开始/结束充电的规则，都在 [services.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py)

从软件设计上看，这是当前项目规模下较合适的方案。

## 6. 服务层设计分析

### 6.1 `QueueService`

[QueueService](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L31-L135) 专门负责“排队位置”的逻辑，关键能力包括：

- `get_active_ticket()` / `deactivate_ticket()`：管理当前有效票据
- `waiting_count()` / `waiting_area_used()`：统计等候区占用
- `pile_occupancy_count()`：统计某桩占用数，包含 `CHARGING + DISPATCHED + PENDING_RESCHEDULE`
- `pile_queue_requests()`：按 `queued_at, id` 取某桩队列中的待充车辆
- `next_queue_num()`：生成 `F/T` 排队号
- `create_waiting_ticket()` / `create_pile_ticket()`：创建或切换票据
- `position_info()`：对外生成“等候区 / 充电区 + ahead_count + pile_id”描述

该服务的意义在于：

- 把“位置”与“状态”分开表达
- 避免在请求服务、会话服务、管理员查询中重复写队列逻辑
- 为后续演示命令、快照导出和前端状态展示提供统一数据来源

### 6.2 `DispatchService`

[DispatchService](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L138-L470) 是 C 部分最核心的服务，负责：

- 获取可调度桩集合
- 估算某桩未来完成耗时
- 选择最优桩
- 进行派桩落库
- 按三种调度模式执行 `normal / single_min_total / batch_min_total`

重要辅助函数包括：

- `_available_piles()`：普通/单次模式下按申请模式筛同类桩
- `_available_batch_piles()`：批量模式下取全部启用桩
- `_estimate_pile_completion_time()`：估算某桩从当前起到清空队列所需时间
- `_dispatch_request_to_pile()`：统一完成派桩副作用
- `try_dispatch_mode()` / `try_dispatch_all()`：调度入口

### 6.3 `ChargingRequestService`

[ChargingRequestService](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L473-L610) 负责请求生命周期前半段：

- `submit_request()`：提交请求、判满、生成队号、创建等候票据、触发调度
- `update_amount()`：允许在等候区时修改充电量
- `update_mode()`：允许在等候区时切换模式，并重新取号与重排
- `get_queue_status()`：对外返回当前排队状态

其中 `submit_request()` 的分支值得注意：

- `normal / single_min_total`：按“等候区是否已满 + 同模式桩是否仍有空位”做接纳判断
- `batch_min_total`：按“站内活跃车辆数是否已达到总容量”做接纳判断

这说明批量调度模式下，系统对“进入站内”的限制逻辑已经独立于普通等候区判满逻辑。

### 6.4 `ChargingSessionService`

[ChargingSessionService](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L613-L862) 负责请求生命周期后半段：

- `start_charging()`：要求请求已被派桩、且必须是该桩队首
- `get_charging_status()`：返回充电进度
- `end_charging()`：结束并结算
- `cancel_charging()`：根据当前状态走取消逻辑
- `_finalize_session()`：统一结束会话、更新桩累计量、生成详单账单、尝试再调度
- `pile_queue_detail()`：为管理员输出某桩队列详细快照

从 C 部分视角看，这个服务的重要性在于：

- 它保证了桩前队列的“队首才能开始充电”约束
- 它在结束和取消时会反向触发 `DispatchService.try_dispatch_all()`，从而驱动整个系统继续运转

## 7. 调度算法设计分析

本节重点解释三种调度模式是如何实现的，以及“总时长最短”在代码里到底通过什么算法完成。

### 7.1 `normal`：FIFO + 在线最短完成时间选桩

入口位于 [DispatchService.try_dispatch_mode](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L399-L428)。

算法过程：

1. 按 `request_time, id` 取当前模式下处于 `QUEUING` 的请求
2. 对每辆车依次处理
3. 在同模式可用桩中，过滤出仍有空位的桩
4. 对每个候选桩计算：
   - `wait_time = _estimate_pile_completion_time(pile)`
   - `self_time = estimate_charge_hours(request.request_amount, request.request_mode)`
   - `score = wait_time + self_time`
5. 选择 `score` 最小的桩，若相同则取更小 `pile.id`
6. 调用 `_dispatch_request_to_pile()` 落库

这是一种典型的在线贪心调度：

- 公平性由 FIFO 保证
- 单车最优由 `wait + self` 最小保证
- 不追求后续全局最优，而追求“当前这辆车现在去哪个桩最好”

### 7.2 `single_min_total`：固定候选集合上的精确最优分配

单次调度的入口在 [DispatchService._try_single_min_total](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L430-L444)，真正的优化算法在 [DispatchService._build_single_min_total_plan](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L263-L376)。

#### 7.2.1 候选集合如何确定

当前实现遵循你之前确认的语义：

- 从等候区选哪些车进入本轮调度时，仍按 FIFO
- 先计算本模式所有桩的剩余空槽数 `available_slots`
- 再按 `request_time, id` 取前 `available_slots` 个请求

也就是说，`single_min_total` 不是“整个等候区都不看顺序”，而是：

- 选车阶段仍 FIFO
- 选中后的这一批车内部，再做最优分配

#### 7.2.2 为什么这是“总时长最短”而不是贪心

当前实现不是逐车调用 `_best_pile_for_request()`，而是对候选集合做完整搜索：

- 用 `assigned` 表示每个桩当前已经分到的请求集合
- 用 `remaining` 表示各桩剩余可分配槽位
- 用 `backtrack(index)` 枚举“第 `index` 个候选请求分到哪个桩”
- 每当形成一个完整分配，就调用 `build_plan_snapshot()` 计算该方案的目标值

目标值 `key` 由三层组成：

- 第一关键字：本轮所有候选请求的总完成时长 `total`
- 第二关键字：按候选请求原顺序形成的 `completion_vector`
- 第三关键字：按候选请求原顺序形成的 `(pile_id, position)` 向量

因此它的优化目标是：

1. 总完成时长最小
2. 若总完成时长相同，则优先让更早到达的请求获得更短完成时间
3. 若仍相同，则按更小的桩号和位次稳定打破平局

#### 7.2.3 为什么桩内顺序按短作业优先

在 `build_plan_snapshot()` 中，每个桩上已分配的请求会先按：

- `request_time[request_id]`，即单车充电时长
- `request_order[request_id]`
- `request_id`

排序后再计算完成时间。

这相当于在固定某个桩的请求集合后，应用“短作业优先（SPT）”原则。对“同一台机器上总完成时间之和最小”这个目标而言，SPT 是最优顺序，因此：

- 桩间分配由回溯搜索决定
- 桩内顺序由 SPT 决定

两者组合后，得到的是“固定候选集合上的精确最优解”。

#### 7.2.4 剪枝是如何做的

`optimistic_lower_bound()` 会计算一个乐观下界：

- 已经分配到各桩的请求，按当前最优顺序累计其完成时间
- 对尚未分配的请求，假设每辆车都能去“当前基准等待时间最小”的可行桩
- 若这个乐观下界都已经大于当前最好方案的总时长，则直接剪枝

因此，当前 `single_min_total` 实现不是“近似”，而是：

- 对本轮候选集合进行的
- 带剪枝的
- 精确搜索算法

### 7.3 `batch_min_total`：严格批次门控下的精确权重分配

批量调度入口位于 [DispatchService._try_batch_dispatch](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L446-L465)，求解算法位于 [DispatchService._build_batch_min_total_plan](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L215-L261)。

#### 7.3.1 批次触发条件

当前代码实现的是“严格批次门控”，核心条件包括：

- 当前没有批次运行中：`_batch_in_progress()` 为假
- 当前启用桩集合固定：`_available_batch_piles()`
- 活跃请求数 `active_count` 必须恰好等于 `total_capacity`
- 且所有活跃请求都必须仍处于 `QUEUING`

对应逻辑：

- `_batch_charging_area_capacity()`：`charging_queue_len * 启用桩数量`
- `_batch_total_capacity()`：`waiting_area_size + charging_area_capacity`
- `_try_batch_dispatch()` 中要求 `active_count == total_capacity` 且 `len(waiting) == active_count`

这意味着：

- 批量调度不是“有空位就继续补车”
- 而是“站内满载、尚无批次运行、一次性整批启动”

#### 7.3.2 为什么当前批量调度可以化简成权重匹配问题

在 `_try_batch_dispatch()` 触发时，代码额外要求：

- 当前没有任何 `DISPATCHED / CHARGING / PENDING_RESCHEDULE` 请求在桩上
- 所有活跃请求都还是 `QUEUING`

因此，本批启动时有一个非常关键的性质：

- 所有桩的基准等待时间都为 0
- 充电区本轮是“从空开始一次性装入一批车”

在这个前提下，某个桩 `p` 上第 `j` 个位置的完成时间贡献可以写成：

- 系数 = `(该桩剩余槽位数 - j + 1) / 桩功率`
- 乘上分配到该位置车辆的请求电量

这就是代码中 `weight` 的来源：

- [services.py:L231-L240](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L231-L240)

即：

- 更靠前的位置权重大
- 功率越大的桩，单位电量耗时越低，因此权重会更优

于是，问题就被化简为：

- 从全部 waiting 中选出 `charging_area_capacity` 辆车进入本批
- 把更小的 `request_amount` 分配给更高权重的槽位

#### 7.3.3 当前算法为什么是“总时长最短”的精确解

当前实现的步骤是：

1. 构造所有可用槽位 `slots`
2. 计算每个槽位的 `weight = (remaining_slots - position + 1) / rated_power`
3. 将全部 waiting 请求按 `(request_amount, request_time, id)` 升序排序，取前 `selected_count`
4. 将槽位按 `(-weight, pile.id, position)` 排序，取前 `selected_count`
5. 将“更小的请求”与“更大权重的槽位”一一配对

这里用到的其实是“重排不等式 / SPT 思想”在当前问题上的直接应用：

- 要最小化 `sum(request_amount_i * weight_i)`
- 最优策略就是让最小的请求电量去匹配最大的槽位权重

因此，当前 `batch_min_total` 不是原先的逐车贪心，而是：

- 在当前“整批启动、基准等待为 0”的建模前提下
- 对目标函数做了精确化简
- 然后给出了对应的精确最优构造解

#### 7.3.4 为什么现在支持跨模式分配

`_available_batch_piles()` 不再按 `request_mode` 过滤桩，而是取所有启用桩，因此：

- 原本申请 `F` 的请求可以被分配到慢充桩
- 原本申请 `T` 的请求也可以被分配到快充桩

并且当前批次一旦启动，中途不再补位，所以不会出现“批次启动后因为跨模式估时还要继续滚动重算”的问题。也正因为如此，之前版本里批量调度的跨模式估时缺陷，在当前严格批次实现下已经不再成立。

### 7.4 `_dispatch_request_to_pile()` 的设计补充

[_dispatch_request_to_pile](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L378-L397) 现在除了更新状态和创建票据外，还做了一件非常关键的事：

- `queued_at = system_now() + timedelta(microseconds=position)`

这样做的目的是：

- 把算法在“计划阶段”确定的桩内位次，稳定反映到数据库排序结果里
- 避免同一时刻批量写入后，后续读取只靠 `id` 导致桩内顺序被冲掉

因此，这个细节是当前单次/批量调度“真实计划顺序能够正确落地”的关键实现点之一。

## 8. 必查逻辑逐项核对

### 8.1 排队号：快充 `F{n}`、慢充 `T{n}`，改模式后重新取号并重排

结论：通过。

依据：

- [QueueService.next_queue_num](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L68-L78)
- [ChargingRequestService.update_mode](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L571-L593)

### 8.2 等候区满判定

结论：通过。

依据：

- 普通/单次模式：`waiting_area_used >= waiting_area_size` 且同模式无空位时拒绝，见 [submit_request](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L515-L535)
- 批量模式：按站内总容量限流，见 [submit_request](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L517-L524)

### 8.3 `waiting_dispatch_paused` 为 true 时停止叫号

结论：通过。

依据：

- [DispatchService.try_dispatch_mode](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L399-L402)

### 8.4 `normal`：FIFO + 最短总完成时间选桩

结论：通过。

依据：

- FIFO：`order_by('request_time', 'id')`
- 单车最优选桩：`_best_pile_for_request()` 计算 `wait + self`

### 8.5 `single_min_total`：按可用槽位数批量派单

结论：通过，且当前已实现“固定候选集合上的总时长最短”。

依据：

- 选车：`[:available_slots]`，见 [services.py:L438-L441](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L438-L441)
- 最优分配：`_build_single_min_total_plan()`，见 [services.py:L263-L376](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L263-L376)

### 8.6 `batch_min_total`：系统满载后全局最优分配

结论：基本通过，且在当前“严格批次”建模前提下，已经实现精确最优分配。

说明：

- 当前实现的“全局”指的是：当一批启动时，在所有 waiting 请求中选出进入充电区的车辆，并对这一批车辆求总完成时长最短
- 它不是无限滚动优化，而是严格批次语义下的批内最优

### 8.7 `_estimate_pile_completion_time`

结论：通过。

依据：

- 会把当前桩的在充会话剩余量和桩前排队请求都计入等待时间，见 [services.py:L186-L199](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L186-L199)

### 8.8 `pile_occupancy_count`

结论：通过。

依据：

- 明确统计 `CHARGING + DISPATCHED + PENDING_RESCHEDULE`，见 [services.py:L49-L59](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/charging/services.py#L49-L59)

### 8.9 `_dispatch_request_to_pile`

结论：通过。

依据：

- 会更新 `request.status/current_pile/queued_at`
- 会创建桩队列票据
- 会同步车辆状态
- 会写 `DispatchRecord`

## 9. 测试与验证说明

### 9.1 已执行测试

本次重新审查时，已在虚拟环境中执行以下测试：

```bash
.venv\Scripts\Activate.ps1
python manage.py test apps.tests.test_single_dispatch_strategy apps.tests.test_batch_dispatch_strategy apps.tests.test_batch_dispatch_command apps.tests.test_acceptance_snapshot apps.tests.test_all_apis --settings=config.settings.test
```

执行结果：

- 共运行 `27` 条测试
- 全部通过
- 返回状态：`OK`

### 9.2 单次调度测试

[test_single_dispatch_strategy.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_single_dispatch_strategy.py) 主要覆盖：

- `test_single_dispatch_keeps_fifo_candidate_selection()`：验证选车阶段仍 FIFO
- `test_single_dispatch_optimizes_selected_batch_globally()`：验证在固定候选集合内，短作业可以排到长作业前，体现全局最优而非逐车贪心
- `test_single_dispatch_keeps_earlier_request_first_on_tie()`：验证并列情况下的稳定 tie-break
- `test_single_dispatch_actual_scenario_with_two_fast_piles()`：验证真实场景下的分配结果与总完成时长
- `RunSingleDispatchCommandTests`：验证 `run_single_dispatch` 命令真实调用算法并输出结果

### 9.3 批量调度测试

[test_batch_dispatch_strategy.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_batch_dispatch_strategy.py) 主要覆盖：

- `test_batch_dispatch_starts_only_when_total_capacity_is_reached()`：验证未满载不启动、满载才启动
- `test_batch_dispatch_does_not_top_up_until_batch_finishes()`：验证批次运行期间中途不补位，必须待批次结束并再次满载后才启动下一批

[test_batch_dispatch_command.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_batch_dispatch_command.py) 主要覆盖：

- `run_batch_dispatch` 命令会生成 CSV
- 终端会输出两批调度详情、跨模式分配清单与非 FIFO 排队证据
- 命令结束后数据库写入会回滚，不污染正式数据

### 9.4 API 与验收快照测试

- [test_all_apis.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_all_apis.py) 覆盖用户请求、改量、改模式、开始/结束/取消充电、管理员查看队列等主 API 链路
- [test_acceptance_snapshot.py](file:///d:/EChargeDispatch_backend/EChargeDispatch/backend/apps/tests/test_acceptance_snapshot.py) 覆盖等候区满判定、故障队列保留等验收快照场景

## 10. 与设计文档的映射关系

### 10.1 与后端框架设计方案的一致之处

当前代码已经把先前设计中的几个关键实体和服务边界落到了实处：

- `accounts.Vehicle` 与 `charging.ChargingRequest` 的关系已经落地
- `QueueTicket` 作为位置票据，而不是单独建 `Queue` 主表的方案已经落地
- `DispatchRecord` 作为调度留痕实体已经落地
- `QueueService` 与 `DispatchService` 的职责边界与设计文档一致

### 10.2 与需求文档的一致之处

当前代码已能体现：

- 等候区与桩前队列的空间划分
- 快充/慢充排号规则
- 正常模式下的最短完成时间选桩
- 单次调度中“先选候选集合，再做整体优化”的策略语义
- 批量调度中“严格批次门控、跨模式分配、批次中途不补位”的策略语义

### 10.3 当前尚未完全对齐之处

仍需明确说明的一点是：

- 题目文本中的批量调度要求“客户请求只需要指定充电量大小”
- 当前实现仍沿用 `request_mode + queue_num(F/T)` 的输入层设计

因此，若后续要做到与题目表述完全一致，建议将批量调度模式下的请求输入形态进一步从 API 层收敛到“只提交充电量”。

## 11. 综合评价

从当前代码实际状态看，C 部分已经不再只是“课程作业可跑通”的程度，而是形成了比较完整、层次较清晰的一套排队与调度实现：

- 模型层：能表达请求、位置、会话和调度留痕
- 视图层：接口清晰，鉴权和响应统一
- 服务层：排队、调度、会话三类职责边界明确
- 算法层：
  - `normal` 为在线 FIFO 贪心
  - `single_min_total` 为固定候选集合上的精确最优搜索
  - `batch_min_total` 为严格批次门控下的精确权重匹配算法
- 测试层：已经同时具备单元/集成/命令/快照多层验证

## 12. 最终结论

本次重新审查后的最终结论如下：

- **主流程正确性：通过**
- **普通调度实现：通过**
- **单次调度实现：通过，且已实现固定候选集合上的总时长最短**
- **批量调度实现：基本通过，且已实现严格批次门控下的整批最优分配**
- **与当前后端设计方案一致性：高**
- **与题目文本的剩余差异：仅剩批量模式输入层仍保留 `request_mode` 语义**

因此，当前 C 部分代码已经可以认为较好地体现了排队与调度模块的设计目标。若后续还要继续提升与题目原文的一致性，优先建议处理批量调度的输入层语义，使其从“算法忽略模式”进一步升级为“接口也不再要求模式”。
