# EChargeDispatch — 智能充电桩调度计费系统

面向课程/验收场景的智能充电站调度与计费系统。用户可提交充电请求、查看排队与详单；管理员可监控充电桩、处理故障、查看报表与调整系统配置。

## 功能概览

| 角色 | 主要能力 |
| --- | --- |
| **用户** | 注册/登录、提交/修改/取消充电请求、查看排队号与前车数量、结束充电、查看充电详单 |
| **管理员** | 登录、启停充电桩、查看桩状态与队列、故障上报与恢复、统计报表、系统参数配置 |
| **服务端** | 排队叫号、最短完成时间调度、峰平谷计费、故障/恢复重调度、验收模拟时钟、详单生成 |

### 业务规则摘要

- **充电站布局**：2 个快充桩（30 度/小时）+ 3 个慢充桩（10 度/小时）；验收默认等候区 **N=10**、每桩队列 **M=3**
- **排队号码**：快充 `F1/F2/...`，慢充 `T1/T2/...`
- **日常调度**：同模式下选择「等待时间 + 自身充电时间」最短的充电桩；有空位即从等候区叫号派队
- **等候区满**：`POST /api/charging/request` 返回 `accepted: false`（`message: 等候区已无空位`），HTTP 仍为 200，不抛业务错误
- **故障处理**（默认优先级调度）：暂停等候区叫号；故障桩队列车辆**留在该桩**等待重调度，有空位则优先派到其它同类型桩；**不**转入等候区
- **故障恢复**：合并同类型**所有桩**上尚未充电的车辆，按排队号整体重调度后，再恢复等候区叫号（恢复时合并；派桩仍用最短完成时间）
- **计费**：总费用 = 充电费（峰/平/谷电价 × 电量）+ 服务费（0.8 元/度 × 电量）

详细需求见 [`docs/智能充电桩调度计费系统详细需求.md`](docs/智能充电桩调度计费系统详细需求.md)。

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
