# EChargeDispatch — 智能充电桩调度计费系统

面向课程/验收场景的智能充电站调度与计费系统。用户可提交充电请求、查看排队与详单；管理员可监控充电桩、处理故障、查看报表与调整系统配置。

## 功能概览

| 角色 | 主要能力 |
| --- | --- |
| **用户** | 注册/登录、提交/修改/取消充电请求、查看排队号与前车数量、结束充电、查看充电详单 |
| **管理员** | 登录、启停充电桩、查看桩状态与队列、故障上报与恢复、统计报表、系统参数配置 |
| **服务端** | 排队叫号、最短完成时间调度、扩展调度（单次/批量）、峰平谷计费、故障/恢复重调度、验收模拟时钟、详单生成 |

### 业务规则摘要

- **充电站布局**：2 个快充桩（30 度/小时）+ 3 个慢充桩（10 度/小时）；验收默认等候区 **N=10**、每桩队列 **M=3**
- **排队号码**：快充 `F1/F2/...`，慢充 `T1/T2/...`
- **日常调度**：同模式下选择「等待时间 + 自身充电时间」最短的充电桩；有空位即从等候区叫号派队
- **等候区满**：`POST /api/charging/request` 返回 `accepted: false`（`message: 等候区已无空位`），HTTP 仍为 200，不抛业务错误
- **故障处理**（默认优先级调度）：暂停等候区叫号；故障桩队列车辆**留在该桩**等待重调度，有空位则优先派到其它同类型桩；**不**转入等候区
- **故障恢复**：合并同类型**所有桩**上尚未充电的车辆，按排队号整体重调度后，再恢复等候区叫号（恢复时合并；派桩仍用最短完成时间）
- **计费**：总费用 = 充电费（峰/平/谷电价 × 电量）+ 服务费（0.8 元/度 × 电量）

详细需求见 [`docs/智能充电桩调度计费系统详细需求.md`](docs/智能充电桩调度计费系统详细需求.md)。

### 扩展调度摘要

系统当前支持 3 种调度模式，对应 `station.SystemConfig.dispatch_mode`：

| 模式 | 含义 | 代码入口 |
| --- | --- | --- |
| `normal` | 日常调度：有空位即叫号；同模式下选择「等待时间 + 自身充电时间」最短的桩 | `apps.charging.services.DispatchService.try_dispatch_mode()` |
| `single_min_total` | 单次调度：候选车辆仍按 FIFO 从等候区选出，但在本轮允许进入充电区的车辆集合确定后，对这批车做整体最优分配 | `apps.charging.services.DispatchService._try_single_min_total()` |
| `batch_min_total` | 批量调度：只有站内总活跃车辆达到总容量时才触发一批；批次一旦启动，中途不补位；下一批需待上一批结束且再次满载后才启动 | `apps.charging.services.DispatchService._try_batch_dispatch()` |

#### 单次调度（`single_min_total`）

- 仍然区分快充/慢充模式，快充请求只在快充桩集合里调度，慢充同理
- 从等候区选择哪些车辆进入本轮调度时，仍按 `request_time` 先来先服务
- 候选集合确定后，不再简单逐车贪心，而是对这批车做整体最优分配，使本轮总完成时长尽量短
- 项目内置演示命令 `run_single_dispatch` 会构造固定场景，直接调用真实算法并输出本轮分配结果与总时长

#### 批量调度（`batch_min_total`）

- 严格按“整批调度”语义实现：仅在**当前无批次运行中**且**站内活跃请求数达到总容量**时启动新一批
- 总容量由 `waiting_area_size + charging_queue_len * 启用充电桩数量` 动态计算，不依赖硬编码常数
- 在批量调度中：
  - 忽略申请时的快慢充模式与到达先后顺序
  - 所有 waiting 请求都可分配到任意启用桩
  - 一次性选出进入充电区的车辆，并按总完成时长最短进行分配
- 批次一旦启动，中途即使出现空位，也不会再从等候区补车；必须等本批结束并再次满载后，才能触发下一批
- 项目内置演示命令 `run_batch_dispatch` 会构造两次批量调度场景，CSV 展示每 5 分钟一组快照，终端展示两批调度的分配详情、跨模式分配清单与非 FIFO 排队证据

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3、Django 6、PyMySQL、PyJWT、django-cors-headers |
| 前端 | Vue 3、Vue Router 4、Vite 8 |
| 数据库 | MySQL 8（开发环境）；测试环境使用 SQLite 内存库 |

## 项目结构

```text
EChargeDispatch/
├── backend/                 # Django 后端
│   ├── apps/
│   │   ├── common/          # 枚举、鉴权、工具、模拟时钟
│   │   ├── accounts/        # 用户/管理员认证
│   │   ├── station/         # 充电站、充电桩、系统配置
│   │   ├── charging/        # 充电请求、排队、调度
│   │   ├── billing/         # 计费策略、详单
│   │   └── operations/      # 故障、报表、验收模拟（run_acceptance）
│   ├── scripts/
│   │   └── generate_backend_docs.py   # 从源码生成架构参考手册
│   ├── config/              # Django 配置与路由
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Vue 3 前端
│   └── src/
│       ├── views/           # 用户端 / 管理端 / 认证页面
│       └── api/             # REST 接口封装
└── docs/                    # 需求、设计、API、架构参考手册
```

## 环境要求

- **Python** ≥ 3.11
- **Node.js** ≥ 20.19 或 ≥ 22.12
- **MySQL** ≥ 8.0（本地开发）

## 快速开始

### 1. 准备数据库

在 MySQL 中创建数据库（名称可与 `.env` 中 `DB_NAME` 一致）：

```sql
CREATE DATABASE echargesys CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 启动后端

```bash
cd backend

# 创建并激活虚拟环境（示例）
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt

# 复制环境变量并按需修改
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

python manage.py migrate
python manage.py init_system   # 初始化充电桩、管理员、计费策略
python manage.py runserver 8080
```

后端默认监听 **http://127.0.0.1:8080**，API 前缀为 `/api`。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器：**http://localhost:5173**，已通过 Vite 代理将 `/api` 转发至后端 `8080` 端口。

### 4. 默认账号

执行 `init_system` 后可用：

| 角色 | 账号 | 密码 |
| --- | --- | --- |
| 管理员 | `A077379` | `123456` |

用户需在登录页注册，使用车牌号/车辆编号作为登录账号。

## 环境变量

在 `backend/.env` 中配置（参考 `backend/.env.example`）：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django 密钥 | — |
| `DJANGO_SETTINGS_MODULE` | 配置模块 | `config.settings.dev` |
| `DB_NAME` | 数据库名 | `echargesys` |
| `DB_USER` | 数据库用户 | `root` |
| `DB_PASSWORD` | 数据库密码 | — |
| `DB_HOST` | 数据库主机 | `127.0.0.1` |
| `DB_PORT` | 数据库端口 | `3306` |

## 运行测试

后端测试使用 SQLite 内存库，无需 MySQL：

```bash
cd backend

# REST 接口集成测试
python manage.py test apps.tests.test_all_apis --settings=config.settings.test

# 验收快照与调度逻辑（V7 可见性、故障队列、恢复重排等）
python manage.py test apps.tests.test_acceptance_snapshot --settings=config.settings.test

# 全部测试
python manage.py test apps.tests --settings=config.settings.test
```

### 调度专项命令

除自动化测试外，项目还提供 2 个用于观察扩展调度行为的演示命令。二者都会调用真实调度算法，并在事务结束时回滚数据库写入，不污染正式数据。

#### 1. 单次调度演示：`run_single_dispatch`

```bash
cd backend
python manage.py run_single_dispatch
```

用途：

- 固定构造一个“已有在充车辆 + 等候区多车”的场景
- 调用 `single_min_total` 真实算法
- 在终端打印本轮各桩分配结果、未进入本轮的车辆和总完成时长

相关代码：

- 命令入口：`apps/operations/management/commands/run_single_dispatch.py`
- 场景构造：`apps/operations/single_dispatch_demo.py`
- 实际算法：`apps/charging/services.py` 中 `DispatchService._try_single_min_total()`

设计说明：

- 命令内部会临时把 `dispatch_mode` 切到 `single_min_total`
- 场景数据全部在事务中构造，命令结束后自动回滚
- 结果是“真实算法跑出来的结果”，而不是硬编码文本

#### 2. 批量调度演示：`run_batch_dispatch`

```bash
cd backend
python manage.py run_batch_dispatch

# 自定义导出路径
python manage.py run_batch_dispatch --output batch_dispatch_result.csv
```

用途：

- 演示严格 `batch_min_total` 的两次批量调度过程
- 第一批：25 辆车陆续到达并满载，触发第一次批量调度
- 第一批运行过程中继续有车辆入站，但不补位
- 第一批结束后再次满载，触发第二次批量调度

输出：

- 终端：仅输出两批调度的策略细节，包括：
  - 触发时刻
  - 每辆车的申请模式、分配桩及桩类型
  - 每辆车完成时长
  - 跨模式分配车辆
  - 非 FIFO 排队证据
  - 每批总完成时长
- CSV：生成 `batch_dispatch_result.csv`，按每 5 分钟一组采样快照输出，列结构与 `run_acceptance` 一致，事件列会写明当前阶段、入站车辆、站内活跃数、是否触发批调及总时长

相关代码：

- 命令入口：`apps/operations/management/commands/run_batch_dispatch.py`
- 演示服务：`apps/operations/batch_dispatch_demo.py`
- 快照复用：`apps/operations/acceptance_service.py` 的 `build_snapshot()` / `validate_snapshot()`
- 实际算法：`apps/charging/services.py` 中 `DispatchService._try_batch_dispatch()` / `_build_batch_min_total_plan()`

设计说明：

- 命令会逐分钟推进模拟时钟，并按 5 分钟粒度落 CSV
- 终端摘要中显示的跨模式分配与非 FIFO 证据，均来自真实算法结果，不是硬编码
- 数据库写入在事务中执行，命令结束后自动回滚；CSV 文件会保留

## 后端架构文档

各 App 的 **Models / Services / Views / 路由** 及核心业务说明，见 [`docs/后端架构参考手册.md`](docs/后端架构参考手册.md)（由脚本从源码 AST 自动生成，含状态流转图）。

修改 `backend/apps/` 下代码后，在项目根目录重新生成：

```bash
python backend/scripts/generate_backend_docs.py
```

校验文档是否与代码同步（可用于 CI）：

```bash
python backend/scripts/generate_backend_docs.py --check
```

**HTML 浏览**（支持侧边目录与 Mermaid 图）：

```bash
cd docs
python -m http.server 8080
# 浏览器打开 http://localhost:8080/后端架构参考手册.html
```

业务逻辑说明等需手工维护的内容，编辑 `backend/scripts/generate_backend_docs.py` 中的 `MANUAL_BUSINESS` 后重新运行生成脚本。

## 作业验收测试

按 [`docs/作业验收用例.md`](docs/作业验收用例.md)（或课程下发的 `作业验收用例.xlsx`）自动执行事件、加速模拟时间（比例尺 **1:10**）并输出与填表格式一致的快照。

### 填表格式说明

与用例表一致：**每个时刻占 3 行**（M=3），时刻/事件/等候区仅在第 1 行填写。

| 列 | 含义 |
| --- | --- |
| 快充1～慢充3 | 每桩 3 行：第 1 行队首（正在充显示电量/费用），第 2～3 行排队车 `(V#,0.00,0.00)` |
| 等候区 | 仅 `queuing` 车辆，多车用 `-` 连接，如 `(V13,F,110.00)-(V14,F,95.00)` |

故障桩上的待重调度车辆显示在**该故障桩队列行**，不写入等候区。

### 1. 执行验收（终端）

```bash
cd backend
python manage.py migrate          # 首次需创建 SimulationClock 表

# 快速调试（事件连续执行，不等待）
python manage.py run_acceptance --fast --until 09:30

# 真实节奏：每 30 秒一条事件（约 21 分钟跑到 09:30）
python manage.py run_acceptance --until 09:30

# 导出 CSV（每个时刻 3 行，可直接对照 xlsx 粘贴）
python manage.py run_acceptance --fast --until 09:30 --output acceptance_result.csv

# 仅查看当前快照
python manage.py run_acceptance --snapshot-only
```

命令流程：重置环境 → 注册 V1–V30 → 虚拟时钟从 **06:00** 起 → 逐条执行用例事件 → 每时刻前自动推进充电/调度/满电结束 → 输出快照并**校验**（所有活跃车辆必须在桩队列或等候区可见）。

**说明**：

- 等候区已满且同模式桩无空位时，该条「到达」事件会被**跳过**（终端提示 `到达被拒：等候区已无空位`），脚本继续执行，不中断
- 车辆到达后自动模拟「插枪」启充；充满请求电量后自动结束并释放桩位
- 导出 CSV 前请关闭已打开的 `acceptance_result.csv`，避免文件占用导致写入失败

### 扩展调度与验收命令的关系

- `run_acceptance`：面向课程验收事件流，关注“按用例推进 + 快照填表”
- `run_single_dispatch`：面向单次调度策略演示，关注“本轮候选集合如何整体最优分配”
- `run_batch_dispatch`：面向批量调度策略演示，关注“两批调度如何触发、为何中途不补位、跨模式分配与非 FIFO 排队如何体现”

三者都会复用同一套后端业务对象与调度服务，但展示目标不同：

- `run_acceptance` 侧重完整业务流程与快照校验
- `run_single_dispatch` 侧重单次调度结果本身
- `run_batch_dispatch` 侧重严格批量调度语义及其结果解释

### 2. 可视化查看（管理端）

1. 另开终端启动后端与前端
2. 管理员登录后打开 **验收快照** 页：`/admin/acceptance`
3. 运行 `run_acceptance` 时该页每 3 秒刷新，展示各桩 `slots`（3 行）与 `table_rows`

### 3. API 快照

```http
GET /api/admin/acceptance/snapshot
Authorization: Bearer <admin-token>
```

模拟时钟开启时返回：`piles[F1…T3].slots`（每桩最多 3 项）、`waiting_area`、`table_rows`（3 行子表）。详见 API 文档 §6.5。

## API 说明

- 所有业务接口统一前缀：`/api`
- 请求/响应格式为 JSON；HTTP 状态码均为 `200`，业务成败由响应体 `code` 字段区分（`0` 为成功）
- 需登录的接口在请求头携带：`Authorization: Bearer <access_token>`

完整接口文档：[`docs/API接口文档.md`](docs/API接口文档.md)

## 前端页面

| 路径 | 说明 |
| --- | --- |
| `/login`、`/register` | 登录 / 注册 |
| `/user` | 用户首页（充电请求、排队状态） |
| `/user/bills` | 充电详单列表 |
| `/admin` | 管理端仪表盘（充电桩概览） |
| `/admin/reports` | 统计报表 |
| `/admin/faults` | 故障管理 |
| `/admin/settings` | 系统配置 |
| `/admin/acceptance` | 验收快照（配合 run_acceptance） |

## 相关文档

| 文档 | 内容 |
| --- | --- |
| [后端架构参考手册](docs/后端架构参考手册.md) | 各 App 类/方法/路由与业务逻辑（自动生成，见上文） |
| [后端架构参考手册（HTML）](docs/后端架构参考手册.html) | 同上，浏览器可读版 |
| [代码审查分工](docs/代码审查分工.md) | 5 人并行审查后端的模块划分与联审清单 |
| [API 接口文档](docs/API接口文档.md) | 全部 HTTP 接口说明 |
| [详细需求](docs/智能充电桩调度计费系统详细需求.md) | 业务规则与验收要求 |
| [Django 后端框架设计](docs/Django后端框架设计方案.md) | 后端模块划分与模型设计 |
| [作业验收用例](docs/作业验收用例.md) | 验收测试场景 |
| [联合验收对接标准](docs/联合验收对接开发标准.md) | 对外联调规范 |

## 生产构建

```bash
# 前端静态资源
cd frontend
npm run build    # 输出至 frontend/dist/

# 后端收集静态文件（如需要）
cd backend
python manage.py collectstatic
```

生产部署时需自行配置 Web 服务器、HTTPS 及数据库安全策略；`.env` 请勿提交至版本库。
