# 智能充电桩调度计费系统 API 接口文档

本文档描述当前后端已实现的全部 HTTP 接口，与代码实现保持一致。

## 1. 基本信息

### 1.1 服务地址

| 环境 | 地址 |
| --- | --- |
| 本地开发 | `http://127.0.0.1:8080` |

所有业务接口统一前缀：`/api`

### 1.2 请求格式

- 请求体使用 **JSON**
- 请求头：

```http
Content-Type: application/json
```

需要登录的接口额外携带：

```http
Authorization: Bearer <access_token>
```

### 1.3 响应格式

所有接口 HTTP 状态码均为 `200`，业务成败由 `code` 字段区分：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功，非 0 表示失败 |
| message | string | 提示信息 |
| data | object / array / null | 业务数据；失败时为 `null` |

### 1.4 认证说明

| 角色 | 获取方式 | Token 有效期 |
| --- | --- | --- |
| 用户 | `POST /api/auth/register` 或 `POST /api/auth/login`（车牌号登录） | 7200 秒 |
| 管理员 | `POST /api/auth/login`（管理员编号登录） | 7200 秒 |

登录时系统根据 `car_id` 自动判断：匹配管理员编号则返回管理员 Token，否则按用户车辆登录。

**默认管理员账号**（`init_system` 初始化后）：

```text
账号：A077379
密码：123456
```

### 1.5 通用错误码

| code | 含义 |
| --- | --- |
| 0 | 成功 |
| 1001 | 参数校验失败 |
| 1002 | 未登录或 token 无效/过期 |
| 1003 | 权限不足 |
| 2001 | 用户不存在 |
| 2002 | 密码错误 |
| 2003 | 用户已注册 |
| 3001 | 已有未完成充电请求 |
| 3002 | 请求不存在 |
| 3003 | 当前状态不允许操作 |
| 3005 | 等候区已满（枚举预留；`POST /api/charging/request` 实际返回 `accepted: false`，不返回此错误码） |
| 4001 | 充电桩不存在 |
| 4002 | 充电桩状态不允许操作 |
| 4003 | 充电桩无空位 |
| 6001 | 账单不存在 |

### 1.6 业务枚举

#### 充电模式 `request_mode`

| 值 | 含义 | 充电功率 |
| --- | --- | --- |
| F | 快充 | 30 度/小时 |
| T | 慢充 | 10 度/小时 |

#### 充电请求状态 `status`

| 值 | 含义 |
| --- | --- |
| queuing | 在等候区排队 |
| dispatched | 已调度至充电区某充电桩队列，等待开始充电 |
| charging | 正在充电 |
| pending_reschedule | 故障后等待重新调度 |
| completed | 已完成 |
| cancelled | 已取消 |

#### 充电桩状态 `pile.status`

| 值 | 含义 |
| --- | --- |
| off | 关闭 |
| standby | 待机（已上电，未投入运行） |
| available | 可用 |
| charging | 充电中 |
| fault | 故障 |

#### 支付状态 `pay_status`

| 值 | 含义 |
| --- | --- |
| unpaid | 未支付 |
| paid | 已支付 |

#### 系统配置枚举

| 字段 | 可选值 |
| --- | --- |
| fault_strategy | `priority`（优先级调度）、`time_order`（时间顺序调度） |
| dispatch_mode | `normal`、`single_min_total`、`batch_min_total` |

---

## 2. 认证接口

### 2.1 用户注册

```http
POST /api/auth/register
```

**权限**：公开

**请求体**：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| car_id | 是 | string | 车牌号/车辆编号，唯一 |
| user_name | 否 | string | 用户姓名，默认取 car_id |
| car_capacity | 否 | number | 电池容量（度），默认 60 |
| password | 是 | string | 登录密码 |

**请求示例**：

```json
{
  "car_id": "V001",
  "user_name": "张三",
  "car_capacity": 60,
  "password": "123456"
}
```

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| access_token | string | JWT Token |
| expires_in | int | 有效期（秒），固定 7200 |
| car_id | string | 车牌号 |
| user_name | string | 用户名 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 7200,
    "car_id": "V001",
    "user_name": "张三"
  }
}
```

**常见错误**：`2003` 用户已注册

---

### 2.2 登录（用户 / 管理员）

```http
POST /api/auth/login
```

**权限**：公开

**请求体**：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| car_id | 是 | string | 用户填车牌号；管理员填管理员编号 |
| password | 是 | string | 密码 |

**用户登录请求示例**：

```json
{
  "car_id": "V001",
  "password": "123456"
}
```

**用户成功响应 `data`**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 7200,
    "role": "user",
    "car_id": "V001"
  }
}
```

**管理员登录请求示例**：

```json
{
  "car_id": "A077379",
  "password": "123456"
}
```

**管理员成功响应 `data`**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 7200,
    "role": "admin",
    "admin_code": "A077379"
  }
}
```

**常见错误**：`2001` 用户不存在、`2002` 密码错误

---

## 3. 用户充电接口

以下接口均需 **用户 Token**。

### 3.1 提交充电请求

```http
POST /api/charging/request
Authorization: Bearer <user-token>
```

**请求体**：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| request_mode | 是 | string | `F` 快充 / `T` 慢充 |
| request_amount | 是 | number | 请求充电量（度），须 > 0 |

**请求示例**：

```json
{
  "request_mode": "F",
  "request_amount": 20
}
```

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| accepted | boolean | 是否受理；`false` 表示等候区已满且同模式桩无空位 |
| reason | string | `accepted=false` 时固定为 `waiting_area_full` |
| message | string | `accepted=false` 时的说明，如「等候区已无空位」 |
| request_id | int | 请求 ID（仅 `accepted=true` 时返回） |
| request_no | string | 请求编号 |
| queue_num | string | 排队号，如 F1、T2 |
| status | string | 请求状态 |
| request_mode | string | 充电模式 |
| request_amount | number | 请求充电量 |
| pile_id | int / null | 已调度时返回目标充电桩 ID |
| position | object / null | 当前位置信息 |
| request_time | string | ISO8601 提交时间 |

等候区满时仍返回 `code: 0`，`data.accepted: false`，不抛业务错误。

**`position` 对象**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| position | string | `等候区` 或 `充电区` |
| queue_num | string | 排队号 |
| ahead_count | int | 前方等待车辆数 |
| pile_id | int | 仅在充电区时返回 |

**响应示例**（已调度到充电区）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "accepted": true,
    "request_id": 1,
    "request_no": "REQA1B2C3D4E5F6",
    "queue_num": "F1",
    "status": "dispatched",
    "request_mode": "F",
    "request_amount": 20.0,
    "pile_id": 1,
    "position": {
      "position": "充电区",
      "queue_num": "F1",
      "ahead_count": 0,
      "pile_id": 1
    },
    "request_time": "2026-06-12T14:30:00+08:00"
  }
}
```

**响应示例**（等候区已满且无法派桩）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "accepted": false,
    "reason": "waiting_area_full",
    "message": "等候区已无空位"
  }
}
```

**业务规则**：
- 同一车辆同时只能有一个未完成请求
- 有空位时系统自动调度，状态可能直接变为 `dispatched`
- 等候区满且同模式桩无空位时返回 `accepted: false`（HTTP 仍为 200，`code` 仍为 0），不抛出 `3005` 错误

---

### 3.2 修改请求充电量

```http
PUT /api/charging/amount
Authorization: Bearer <user-token>
```

**限制**：仅 `status = queuing`（仍在等候区）时可修改，排队号不变。

**请求体**：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| amount | 是 | number | 新的请求充电量，须 > 0 |

**请求示例**：

```json
{
  "amount": 25
}
```

**成功响应**：与 [3.1 提交充电请求](#31-提交充电请求) 的 `data` 结构相同（不含 `accepted` 字段）。

**常见错误**：`3003` 已进入充电区或正在充电

---

### 3.3 修改充电模式

```http
PUT /api/charging/mode
Authorization: Bearer <user-token>
```

**限制**：仅 `status = queuing` 时可修改。修改后重新生成排队号，进入新模式队列末尾。

**请求体**：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| mode | 是 | string | `F` 或 `T` |

**请求示例**：

```json
{
  "mode": "T"
}
```

**成功响应**：与 [3.1](#31-提交充电请求) 相同（不含 `accepted` 字段），`queue_num` 会更新。

---

### 3.4 查询排队状态

```http
GET /api/charging/queue-status
Authorization: Bearer <user-token>
```

**无请求体**

**成功响应 `data`（有活跃请求）**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| has_request | bool | 是否有未完成请求 |
| request_id | int | 请求 ID |
| queue_num | string | 排队号 |
| status | string | 请求状态 |
| request_mode | string | 充电模式 |
| ahead_count | int | 前方等待车辆数 |
| position | object / null | 位置信息，结构同 3.1 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "has_request": true,
    "request_id": 1,
    "queue_num": "F1",
    "status": "dispatched",
    "request_mode": "F",
    "ahead_count": 0,
    "position": {
      "position": "充电区",
      "queue_num": "F1",
      "ahead_count": 0,
      "pile_id": 1
    }
  }
}
```

**无活跃请求时**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "has_request": false
  }
}
```

---

### 3.5 开始充电

```http
POST /api/charging/start
Authorization: Bearer <user-token>
```

**前置条件**：
- 请求状态为 `dispatched`
- 车辆在该充电桩队列中排在第一位
- `pile_id` 与请求当前所属桩一致

**请求体**：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| pile_id | 是 | int | 充电桩 ID |

**请求示例**：

```json
{
  "pile_id": 1
}
```

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| session_id | int | 充电会话 ID |
| request_id | int | 请求 ID |
| pile_id | int | 充电桩 ID |
| status | string | 固定为 `charging` |
| start_time | string | ISO8601 开始时间 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": 1,
    "request_id": 1,
    "pile_id": 1,
    "status": "charging",
    "start_time": "2026-06-12T14:35:00+08:00"
  }
}
```

---

### 3.6 查询充电状态

```http
GET /api/charging/status
Authorization: Bearer <user-token>
```

**成功响应 `data`（正在充电）**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| has_request | bool | 是否有活跃请求 |
| request_id | int | 请求 ID |
| status | string | 请求状态 |
| request_mode | string | 充电模式 |
| request_amount | number | 请求充电量 |
| charged_amount | number | 当前已充电量（实时估算） |
| pile_id | int | 充电桩 ID |
| session_id | int / null | 会话 ID |
| start_time | string / null | 充电开始时间 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "has_request": true,
    "request_id": 1,
    "status": "charging",
    "request_mode": "F",
    "request_amount": 20.0,
    "charged_amount": 2.5,
    "pile_id": 1,
    "session_id": 1,
    "start_time": "2026-06-12T14:35:00+08:00"
  }
}
```

---

### 3.7 结束充电

```http
POST /api/charging/end
Authorization: Bearer <user-token>
```

**前置条件**：`status = charging`

**无请求体**

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| request_id | int | 请求 ID |
| status | string | 固定为 `completed` |
| charged_amount | number | 实际充电量 |
| bill_id | int | 生成的账单 ID |
| detail_id | int | 生成的详单 ID |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "request_id": 1,
    "status": "completed",
    "charged_amount": 5.0,
    "bill_id": 1,
    "detail_id": 1
  }
}
```

---

### 3.8 取消充电

```http
DELETE /api/charging/cancel
Authorization: Bearer <user-token>
```

**说明**：
- 等候区、充电区排队、故障待重调度（`pending_reschedule`）均可取消
- 正在充电时取消，按已充电量生成详单和账单

**无请求体**

**成功响应 `data`（排队中取消）**：

```json
{
  "request_id": 1,
  "status": "cancelled"
}
```

**成功响应 `data`（充电中取消）**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| request_id | int | 请求 ID |
| status | string | 响应中为 `completed`（`_finalize_session` 返回值）；数据库中请求状态为 `cancelled` |
| charged_amount | number | 实际充电量 |
| bill_id | int | 生成的账单 ID |
| detail_id | int | 生成的详单 ID |

```json
{
  "request_id": 1,
  "status": "completed",
  "charged_amount": 2.5,
  "bill_id": 1,
  "detail_id": 1
}
```

---

## 4. 账单接口

以下接口均需 **用户 Token**。

### 4.1 账单列表

```http
GET /api/bill/list
Authorization: Bearer <user-token>
```

**成功响应 `data`**：账单数组

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| bill_id | int | 账单 ID |
| bill_no | string | 账单编号 |
| bill_date | string | 账单日期 YYYY-MM-DD |
| total_fee | number | 总费用 |
| pay_status | string | 支付状态 |
| created_at | string | 创建时间 ISO8601 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "bill_id": 1,
      "bill_no": "BILLA1B2C3D4E5",
      "bill_date": "2026-06-12",
      "total_fee": 9.0,
      "pay_status": "unpaid",
      "created_at": "2026-06-12T14:40:00+08:00"
    }
  ]
}
```

---

### 4.2 账单详单

```http
GET /api/bill/detail/{bill_id}
Authorization: Bearer <user-token>
```

**路径参数**：`bill_id` — 账单 ID

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| bill_id | int | 账单 ID |
| bill_no | string | 账单编号 |
| bill_date | string | 账单日期 |
| total_charge_amount | number | 总充电量 |
| total_charge_duration | number | 总充电时长（小时） |
| total_charge_fee | number | 总充电费 |
| total_service_fee | number | 总服务费 |
| total_fee | number | 总费用 |
| pay_status | string | 支付状态 |
| details | array | 详单列表 |

**`details[]` 元素**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| detail_no | string | 详单编号 |
| generated_at | string | 生成时间 |
| pile_no | string | 充电桩编号 |
| charge_amount | number | 充电量 |
| charge_duration | number | 充电时长 |
| start_time | string | 开始时间 |
| end_time | string | 结束时间 |
| charge_fee | number | 充电费 |
| service_fee | number | 服务费 |
| total_fee | number | 总费用 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "bill_id": 1,
    "bill_no": "BILLA1B2C3D4E5",
    "bill_date": "2026-06-12",
    "total_charge_amount": 5.0,
    "total_charge_duration": 0.1667,
    "total_charge_fee": 3.5,
    "total_service_fee": 4.0,
    "total_fee": 7.5,
    "pay_status": "unpaid",
    "details": [
      {
        "detail_no": "DETA1B2C3D4E5",
        "generated_at": "2026-06-12T14:40:00+08:00",
        "pile_no": "F1",
        "charge_amount": 5.0,
        "charge_duration": 0.1667,
        "start_time": "2026-06-12T14:35:00+08:00",
        "end_time": "2026-06-12T14:45:00+08:00",
        "charge_fee": 3.5,
        "service_fee": 4.0,
        "total_fee": 7.5
      }
    ]
  }
}
```

---

### 4.3 支付账单

```http
POST /api/bill/pay/{bill_id}
Authorization: Bearer <user-token>
```

**路径参数**：`bill_id` — 账单 ID

**无请求体**

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| bill_id | int | 账单 ID |
| pay_status | string | 支付状态 |
| paid_at | string | 支付时间 ISO8601（仅首次支付成功时返回） |

**响应示例**（首次支付）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "bill_id": 1,
    "pay_status": "paid",
    "paid_at": "2026-06-12T14:42:00+08:00"
  }
}
```

**响应示例**（已支付，重复调用）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "bill_id": 1,
    "pay_status": "paid"
  }
}
```

---

## 5. 管理员接口 — 系统配置与充电桩

以下接口均需 **管理员 Token**。

### 5.1 查询 / 修改系统参数

```http
GET /api/admin/system-config
PUT /api/admin/system-config
Authorization: Bearer <admin-token>
```

**GET 成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| station_id | string | 站点编号 |
| fast_pile_num | int | 快充桩数量 |
| slow_pile_num | int | 慢充桩数量 |
| waiting_area_size | int | 等候区容量 |
| charging_queue_len | int | 每桩排队队列长度 |
| fault_strategy | string | 故障调度策略 |
| dispatch_mode | string | 普通调度模式 |
| service_price | number | 服务费单价（元/度） |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "station_id": "BUPT-01",
    "fast_pile_num": 2,
    "slow_pile_num": 3,
    "waiting_area_size": 10,
    "charging_queue_len": 3,
    "fault_strategy": "priority",
    "dispatch_mode": "normal",
    "service_price": 0.8
  }
}
```

**PUT 请求体**（字段均可选，只更新传入的字段）：

```json
{
  "fast_pile_num": 2,
  "slow_pile_num": 3,
  "waiting_area_size": 10,
  "charging_queue_len": 3,
  "fault_strategy": "priority",
  "dispatch_mode": "normal"
}
```

**PUT 成功响应**：返回更新后的完整配置，结构同 GET。

---

### 5.2 查询所有充电桩状态

```http
GET /api/pile/status
Authorization: Bearer <admin-token>
```

**成功响应 `data`**：充电桩数组

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| pile_id | int | 充电桩 ID |
| pile_no | string | 桩编号，如 F1、T2 |
| mode | string | 充电模式 F/T |
| mode_label | string | 模式中文名 |
| power | number | 额定功率（度/小时） |
| status | string | 桩状态 |
| queue_used | int | 当前队列占用数 |
| queue_total | int | 队列容量 |
| current_car | object / null | 当前充电车辆 |
| total_charge_num | int | 累计充电次数 |
| total_charge_time | number | 累计充电时长 |
| total_charge_capacity | number | 累计充电量 |

**`current_car` 对象**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| car_id | string | 车牌号 |
| request_id | int | 请求 ID |
| charged_amount | number | 已充电量 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "pile_id": 1,
      "pile_no": "F1",
      "mode": "F",
      "mode_label": "快充",
      "power": 30.0,
      "status": "available",
      "queue_used": 0,
      "queue_total": 3,
      "current_car": null,
      "total_charge_num": 0,
      "total_charge_time": 0.0,
      "total_charge_capacity": 0.0
    }
  ]
}
```

---

### 5.3 查看充电桩队列

```http
GET /api/queue/pile/{pile_id}
Authorization: Bearer <admin-token>
```

**路径参数**：`pile_id` — 充电桩 ID

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| pile_id | int | 充电桩 ID |
| pile_no | string | 桩编号 |
| status | string | 桩状态 |
| queue_used | int | 当前队列占用数（含在充、排队、待重调度） |
| queue_total | int | 队列容量（等于 `charging_queue_len`） |
| queue | array | 队列明细，按顺位排列（含正在充电的车辆） |
| charging_car | object / null | 正在充电车辆摘要（与 `queue` 队首重复，便于展示） |

**`queue[]` 元素**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| request_id | int | 请求 ID |
| car_id | string | 车牌号 |
| user_id | int | 用户 ID |
| battery_capacity | number | 电池容量 |
| request_amount | number | 请求充电量 |
| queue_num | string | 排队号 |
| waiting_seconds | int | 等待秒数（在充时为已充时长） |
| status | string | `charging` / `dispatched` / `pending_reschedule` |
| position | int | 队列顺位（从 1 起） |
| charged_amount | number | 可选；`status=charging` 时返回当前已充电量 |

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "pile_id": 1,
    "pile_no": "F1",
    "status": "charging",
    "queue_used": 2,
    "queue_total": 3,
    "queue": [
      {
        "request_id": 1,
        "car_id": "V001",
        "user_id": 1,
        "battery_capacity": 60.0,
        "request_amount": 20.0,
        "queue_num": "F1",
        "waiting_seconds": 300,
        "status": "charging",
        "position": 1,
        "charged_amount": 3.5
      },
      {
        "request_id": 2,
        "car_id": "V002",
        "user_id": 2,
        "battery_capacity": 60.0,
        "request_amount": 15.0,
        "queue_num": "F2",
        "waiting_seconds": 120,
        "status": "dispatched",
        "position": 2
      }
    ],
    "charging_car": {
      "car_id": "V001",
      "request_id": 1,
      "charged_amount": 3.5
    }
  }
}
```

---

### 5.4 启动充电桩（上电）

```http
POST /api/pile/{pile_id}/poweron
Authorization: Bearer <admin-token>
```

将关闭状态的桩切换为 `standby`。无请求体。

**成功响应 `data`**：单个充电桩对象，结构同 [5.2](#52-查询所有充电桩状态) 数组元素。

---

### 5.5 投入运行

```http
POST /api/pile/{pile_id}/start
Authorization: Bearer <admin-token>
```

将桩切换为 `available` 并触发调度。无请求体。

---

### 5.6 关闭充电桩

```http
POST /api/pile/{pile_id}/poweroff
Authorization: Bearer <admin-token>
```

**限制**：桩上无排队车辆且无正在进行的充电会话。

无请求体。成功响应结构同 [5.4](#54-启动充电桩上电)。

**常见错误**：`4002` 桩上仍有车辆

---

## 6. 管理员接口 — 故障与报表

### 6.1 故障上报

```http
POST /api/admin/fault/report
Authorization: Bearer <admin-token>
```

**请求体**：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| pile_id | 是 | int | 故障充电桩 ID |

**请求示例**：

```json
{
  "pile_id": 1
}
```

**成功响应 `data`**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "fault_id": 1,
    "pile_id": 1,
    "affected_count": 2
  }
}
```

**说明**：
- 暂停等候区叫号（`waiting_dispatch_paused = true`）
- 正在充电的车辆立即停止并按已充电量生成详单，请求进入 `pending_reschedule` 并留在故障桩
- 该桩 `dispatched` 排队车辆进入 `pending_reschedule`，优先重调度至其它同类型桩；无空位则留在故障桩队列

---

### 6.2 故障恢复

```http
POST /api/admin/fault/recover
Authorization: Bearer <admin-token>
```

**请求体**：

```json
{
  "pile_id": 1
}
```

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| pile_id | int | 充电桩 ID |
| status | string | 恢复后桩状态：`available`（已投入运行）或 `standby`（未投入运行） |

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "pile_id": 1,
    "status": "available"
  }
}
```

恢复后若同类型桩有待合并队列，会按排队号整体重调度，并恢复等候区叫号。

---

### 6.3 故障记录列表

```http
GET /api/admin/fault/list
Authorization: Bearer <admin-token>
```

**成功响应 `data`**：故障记录数组

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| fault_id | int | 故障 ID |
| pile_id | int | 充电桩 ID |
| pile_no | string | 桩编号 |
| fault_type | string | 故障类型 |
| fault_status | string | `open` / `recovered` |
| occurred_at | string | 发生时间 |
| recovered_at | string / null | 恢复时间 |
| description | string | 故障说明 |

---

### 6.4 统计报表

```http
GET /api/admin/report/stats?period=day&date=2026-06-12
Authorization: Bearer <admin-token>
```

**查询参数**：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| period | 是 | `day` / `week` / `month` |
| date | 是 | 日报/周报：`YYYY-MM-DD`；月报：`YYYY-MM` |

**示例**：

```http
GET /api/admin/report/stats?period=day&date=2026-06-12
GET /api/admin/report/stats?period=week&date=2026-06-12
GET /api/admin/report/stats?period=month&date=2026-06
```

**成功响应 `data`**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| period | string | 统计周期 |
| date | string | 查询日期 |
| items | array | 各充电桩统计数据 |

**`items[]` 元素**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| pile_id | int | 充电桩 ID |
| pile_no | string | 桩编号 |
| period | string | 统计周期 |
| date | string | 查询日期 |
| total_charge_num | int | 充电次数 |
| total_charge_time | number | 累计充电时长 |
| total_charge_capacity | number | 累计充电量 |
| total_charge_fee | number | 累计充电费 |
| total_service_fee | number | 累计服务费 |
| total_fee | number | 累计总费用 |

---

### 6.5 验收填表快照

配合 `python manage.py run_acceptance` 使用。模拟时钟开启时，返回与作业验收用例表一致的各桩/等候区状态。

```http
GET /api/admin/acceptance/snapshot
Authorization: Bearer <admin-token>
```

**可选查询参数**：`case_time` — 填表时刻标签，如 `06:05`

**成功响应 `data`**：

| 字段 | 说明 |
| --- | --- |
| case_time | 请求参数中的填表时刻标签；未传时为当前模拟时间的 `HH:MM` |
| sim_time | 当前模拟时间 ISO8601 |
| sim_active | 模拟时钟是否开启 |
| queue_rows | 每个时刻子表行数（等于 `charging_queue_len`，验收默认 3） |
| piles | 各桩状态，键为 F1/F2/T1/T2/T3 |
| waiting_area | 等候区占用与车辆列表 |
| table_rows | 填表子表（3 行），与作业用例 xlsx 一致 |
| table_row | 兼容字段，等同 `table_rows[0]` |

**`waiting_area` 对象**：

| 字段 | 说明 |
| --- | --- |
| display | 填表用字符串，多车用 `-` 连接 |
| used | 当前等候区占用数 |
| capacity | 等候区容量 |
| items | 等候区车辆明细数组 |

**`piles[桩编号]`**：

| 字段 | 说明 |
| --- | --- |
| slots | 最多 3 个填表字符串，队首为已充电量/费用，排队为 `(V2,0.00,0.00)` |
| display | 队首填表字符串（等同 `slots[0]`） |
| car_id | 队首车辆 |
| charged_amount | 队首已充电量 |
| current_fee | 队首当前费用（充电费+服务费） |

**`table_rows[i]`**：`时刻`、`快充1`…`慢充3`、`等候区`；仅 `i=0` 时填写时刻与等候区，其余行对应各桩第 2、3 排队位。

---

## 7. 计费规则说明

系统按以下规则计算费用（结束充电或故障/取消中断时生成详单）：

```text
充电费 = 分时段单价 × 实际充电度数（跨时段自动拆分）
服务费 = 0.8 × 实际充电度数
总费用 = 充电费 + 服务费
```

**分时电价**：

| 时段 | 时间 | 单价（元/度） |
| --- | --- | --- |
| 峰时 | 10:00–15:00，18:00–21:00 | 1.0 |
| 平时 | 7:00–10:00，15:00–18:00，21:00–23:00 | 0.7 |
| 谷时 | 23:00–次日 7:00 | 0.4 |

---

## 8. 典型调用流程

### 8.1 用户完整充电流程

```text
1. POST /api/auth/register          注册
2. POST /api/auth/login             登录，获取 user token
3. POST /api/charging/request       提交充电请求
4. GET  /api/charging/queue-status  查询排队（直到 status=dispatched）
5. POST /api/charging/start         开始充电（须为队列第一位）
6. GET  /api/charging/status        查询充电进度
7. POST /api/charging/end           结束充电，生成账单
8. GET  /api/bill/list              查看账单
9. GET  /api/bill/detail/{bill_id}  查看详单
10. POST /api/bill/pay/{bill_id}    支付
```

### 8.2 管理员运维流程

```text
1. POST /api/auth/login                  管理员登录
2. GET  /api/admin/system-config         查看系统参数
3. GET  /api/pile/status                 查看所有充电桩
4. GET  /api/queue/pile/{pile_id}        查看某桩队列
5. POST /api/admin/fault/report          上报故障
6. GET  /api/admin/fault/list            查看故障记录
7. POST /api/admin/fault/recover         恢复故障
8. GET  /api/admin/report/stats          查看报表
```

---

## 9. curl 调用示例

### 用户注册并充电

```powershell
# 注册
curl.exe -X POST http://127.0.0.1:8080/api/auth/register `
  -H "Content-Type: application/json" `
  -d "{\"car_id\":\"V001\",\"user_name\":\"张三\",\"car_capacity\":60,\"password\":\"123456\"}"

# 登录
curl.exe -X POST http://127.0.0.1:8080/api/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"car_id\":\"V001\",\"password\":\"123456\"}"

# 提交充电请求（将 <user-token> 替换为登录返回的 access_token）
curl.exe -X POST http://127.0.0.1:8080/api/charging/request `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <user-token>" `
  -d "{\"request_mode\":\"F\",\"request_amount\":20}"

# 开始充电
curl.exe -X POST http://127.0.0.1:8080/api/charging/start `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <user-token>" `
  -d "{\"pile_id\":1}"

# 结束充电
curl.exe -X POST http://127.0.0.1:8080/api/charging/end `
  -H "Authorization: Bearer <user-token>"
```

### 管理员查询桩状态

```powershell
# 管理员登录
curl.exe -X POST http://127.0.0.1:8080/api/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"car_id\":\"A077379\",\"password\":\"123456\"}"

# 查询充电桩（将 <admin-token> 替换为登录返回的 access_token）
curl.exe http://127.0.0.1:8080/api/pile/status `
  -H "Authorization: Bearer <admin-token>"
```

---

## 10. 接口总览

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | 公开 | 用户注册 |
| POST | `/api/auth/login` | 公开 | 用户/管理员登录 |
| POST | `/api/charging/request` | 用户 | 提交充电请求 |
| PUT | `/api/charging/amount` | 用户 | 修改充电量 |
| PUT | `/api/charging/mode` | 用户 | 修改充电模式 |
| GET | `/api/charging/queue-status` | 用户 | 查询排队状态 |
| POST | `/api/charging/start` | 用户 | 开始充电 |
| GET | `/api/charging/status` | 用户 | 查询充电状态 |
| POST | `/api/charging/end` | 用户 | 结束充电 |
| DELETE | `/api/charging/cancel` | 用户 | 取消充电 |
| GET | `/api/bill/list` | 用户 | 账单列表 |
| GET | `/api/bill/detail/{bill_id}` | 用户 | 账单详单 |
| POST | `/api/bill/pay/{bill_id}` | 用户 | 支付账单 |
| GET | `/api/admin/system-config` | 管理员 | 查询系统参数 |
| PUT | `/api/admin/system-config` | 管理员 | 修改系统参数 |
| GET | `/api/pile/status` | 管理员 | 查询所有充电桩 |
| GET | `/api/queue/pile/{pile_id}` | 管理员 | 查看充电桩队列 |
| POST | `/api/pile/{pile_id}/poweron` | 管理员 | 启动充电桩 |
| POST | `/api/pile/{pile_id}/start` | 管理员 | 投入运行 |
| POST | `/api/pile/{pile_id}/poweroff` | 管理员 | 关闭充电桩 |
| POST | `/api/admin/fault/report` | 管理员 | 故障上报 |
| POST | `/api/admin/fault/recover` | 管理员 | 故障恢复 |
| GET | `/api/admin/fault/list` | 管理员 | 故障记录列表 |
| GET | `/api/admin/report/stats` | 管理员 | 统计报表 |
| GET | `/api/admin/acceptance/snapshot` | 管理员 | 验收填表快照 |
