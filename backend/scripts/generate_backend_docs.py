#!/usr/bin/env python3
"""
从 backend/apps 源码自动生成后端架构参考手册。

用法:
    python backend/scripts/generate_backend_docs.py
    python backend/scripts/generate_backend_docs.py --check   # CI：与已生成文档比对，不一致则退出 1

输出: docs/后端架构参考手册.md
"""

from __future__ import annotations

import argparse
import ast
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPS_DIR = ROOT / "backend" / "apps"
OUTPUT = ROOT / "docs" / "后端架构参考手册.md"

APP_ORDER = ["common", "accounts", "station", "charging", "billing", "operations"]

# 手工维护的业务说明（改业务逻辑时同步更新此段）
MANUAL_BUSINESS = {
    "accounts": """
**职责**：用户/管理员认证、车辆账户管理。

- 注册：车牌号唯一，同时创建 `UserAccount` + `Vehicle`，返回 JWT（含 vehicle_id）。
- 登录：先查管理员（admin_code），再查车辆（plate_no）；密码 bcrypt 校验。
""",
    "station": """
**职责**：充电站、系统配置、充电桩生命周期。

- 桩状态机：`off → standby → available ↔ charging`，故障时为 `fault`。
- `start_pile` 投入运行后触发全局调度 `DispatchService.try_dispatch_all()`。
- `SystemConfig` 控制等候区容量、桩队列长度、调度模式、故障策略等。
""",
    "charging": """
**职责**：充电请求、排队、调度、会话核心流程。

**请求状态流转**：
`queuing`（等候区）→ `dispatched`（桩队列）→ `charging` → `completed` / `cancelled`；
故障时 → `pending_reschedule` → 重调度后回到 `dispatched`。

**调度策略**（`dispatch_mode`）：
- `normal`：FIFO，有空位即按最短总完成时间选桩。
- `single_min_total`：每轮按可用槽位数批量派单。
- `batch_min_total`：系统满载后一次性全局最优分配。

**队列号**：快充 `F{n}`、慢充 `T{n}`，由 `SystemConfig` 序号递增生成。
""",
    "billing": """
**职责**：分时电价计费、账单生成与支付。

- 充电结束（`_finalize_session`）时调用 `BillingService.create_detail_and_bill`。
- 充电费按时段（峰/平/谷）跨时段分摊；服务费 = 电量 × 0.8 元/度。
- 每次会话生成一条 `ChargeDetail` 和一张 `Bill`（一账单一明细）。
""",
    "operations": """
**职责**：故障上报/恢复、重调度、运营报表、验收自动化。

- 故障上报：暂停等候区叫号 → 结束在充会话 → 队列车辆标记 `pending_reschedule` → 优先重调度。
- 故障恢复：同类型桩合并未充电队列，按排队号整体重分配。
- `AcceptanceService`：验收模拟时钟驱动，自动满电结束、自动启充、生成填表快照。
""",
    "common": """
**职责**：跨模块基础设施。

- `system_now()`：模拟时钟开启时返回虚拟时间，否则真实时间。
- `api_view` / `require_user` / `require_admin`：统一异常捕获与 JWT 鉴权。
- `compute_charged_amount`：已充电量 = min(功率×时长, 请求电量)。
""",
}


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_docstring(node) -> str:
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value.value.strip()
    return ""


def format_args(args: ast.arguments) -> str:
    parts = []
    for arg in args.args:
        if arg.arg == "self":
            continue
        parts.append(arg.arg)
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    for arg in args.kwonlyargs:
        parts.append(arg.arg)
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
    return ", ".join(parts)


def extract_class_info(node: ast.ClassDef) -> dict:
    bases = [ast.unparse(b) for b in node.bases]
    fields = []
    methods = []
    properties = []
    meta = {}

    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            val = ast.unparse(item.value) if item.value else ""
            fields.append((item.target.id, val))
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    val = ast.unparse(item.value) if item.value else ""
                    fields.append((target.id, val))
        elif isinstance(item, ast.FunctionDef):
            if item.name == "Meta":
                for sub in item.body:
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                meta[t.id] = ast.unparse(sub.value)
            elif item.decorator_list:
                dec_names = []
                for d in item.decorator_list:
                    if isinstance(d, ast.Name):
                        dec_names.append(d.id)
                    elif isinstance(d, ast.Attribute):
                        dec_names.append(d.attr)
                if "property" in dec_names:
                    properties.append((item.name, get_docstring(item)))
                else:
                    methods.append(
                        {
                            "name": item.name,
                            "args": format_args(item.args),
                            "doc": get_docstring(item),
                            "decorators": dec_names,
                            "is_static": "staticmethod" in dec_names,
                            "is_class": "classmethod" in dec_names,
                        }
                    )
            else:
                methods.append(
                    {
                        "name": item.name,
                        "args": format_args(item.args),
                        "doc": get_docstring(item),
                        "decorators": [],
                        "is_static": False,
                        "is_class": False,
                    }
                )

    return {
        "name": node.name,
        "bases": bases,
        "doc": get_docstring(node),
        "fields": fields,
        "methods": methods,
        "properties": properties,
        "meta": meta,
    }


def extract_module_functions(tree: ast.Module) -> list[dict]:
    funcs = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        decorators = []
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorators.append(d.id)
            elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
                args_str = ", ".join(ast.unparse(a) for a in d.args)
                decorators.append(f"{d.func.id}({args_str})")
            elif isinstance(d, ast.Attribute):
                decorators.append(d.attr)
        funcs.append(
            {
                "name": node.name,
                "args": format_args(node.args),
                "doc": get_docstring(node),
                "decorators": decorators,
            }
        )
    return funcs


def parse_py_file(path: Path) -> dict:
    source = read_source(path)
    tree = ast.parse(source, filename=str(path))
    classes = [extract_class_info(n) for n in tree.body if isinstance(n, ast.ClassDef)]
    functions = extract_module_functions(tree)
    return {"path": path, "classes": classes, "functions": functions}


def find_url_routes(app: str) -> list[tuple[str, str]]:
    urls_path = APPS_DIR / app / "urls.py"
    if not urls_path.exists():
        return []
    tree = ast.parse(read_source(urls_path))
    routes = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "urlpatterns":
                for elt in node.value.elts:
                    if not isinstance(elt, ast.Call):
                        continue
                    path_arg = elt.args[0].value if elt.args and isinstance(elt.args[0], ast.Constant) else "?"
                    view = "?"
                    if len(elt.args) >= 2:
                        v = elt.args[1]
                        if isinstance(v, ast.Attribute):
                            view = v.attr
                    routes.append((path_arg, view))
    return routes


def render_class(cls: dict) -> list[str]:
    lines = [f"#### `{cls['name']}`"]
    if cls["bases"]:
        lines.append(f"- **继承**: `{', '.join(cls['bases'])}`")
    if cls["doc"]:
        lines.append(f"- **说明**: {cls['doc']}")
    if cls["meta"]:
        meta_parts = [f"`{k}`={v}" for k, v in cls["meta"].items()]
        lines.append(f"- **Meta**: {', '.join(meta_parts)}")
    if cls["fields"]:
        lines.append("- **字段/属性**:")
        for name, default in cls["fields"]:
            if default:
                lines.append(f"  - `{name}` — 默认/值: `{default}`")
            else:
                lines.append(f"  - `{name}`")
    if cls["properties"]:
        lines.append("- **@property**:")
        for name, doc in cls["properties"]:
            doc_part = f" — {doc}" if doc else ""
            lines.append(f"  - `{name}`{doc_part}")
    if cls["methods"]:
        lines.append("- **方法**:")
        for m in cls["methods"]:
            decs = []
            if m["is_static"]:
                decs.append("@staticmethod")
            if m["is_class"]:
                decs.append("@classmethod")
            for d in m["decorators"]:
                if d not in ("staticmethod", "classmethod", "property"):
                    decs.append(f"@{d}")
            dec_str = f" ({', '.join(decs)})" if decs else ""
            doc = f" — {m['doc']}" if m["doc"] else ""
            lines.append(f"  - `{m['name']}({m['args']})`{dec_str}{doc}")
    lines.append("")
    return lines


def render_functions(funcs: list[dict], title: str = "视图函数") -> list[str]:
    if not funcs:
        return []
    lines = [f"### {title}", ""]
    for f in funcs:
        dec = ", ".join(f["decorators"])
        dec_str = f" `[{dec}]`" if dec else ""
        doc = f" — {f['doc']}" if f["doc"] else ""
        lines.append(f"- **`{f['name']}({f['args']})`**{dec_str}{doc}")
    lines.append("")
    return lines


COMMON_EXTRA = ["enums.py", "decorators.py", "auth.py", "utils.py", "sim_clock.py", "exceptions.py", "responses.py"]


def render_app_section(app: str) -> list[str]:
    app_dir = APPS_DIR / app
    if not app_dir.is_dir():
        return []

    lines = [f"## {app}", ""]
    if app in MANUAL_BUSINESS:
        lines.append("### 业务概述")
        lines.append(MANUAL_BUSINESS[app].strip())
        lines.append("")

    extra_py = COMMON_EXTRA if app == "common" else []
    file_specs = [(f, f.replace(".py", "").replace("_", " ").title()) for f in extra_py]
    file_specs += [
        ("models.py", "Models"),
        ("services.py", "Services"),
        ("views.py", "Views"),
    ]

    for filename, kind in file_specs:
        path = app_dir / filename
        if not path.exists():
            continue
        parsed = parse_py_file(path)
        lines.append(f"### {kind} (`apps/{app}/{filename}`)")
        lines.append("")
        if parsed["classes"]:
            for cls in parsed["classes"]:
                lines.extend(render_class(cls))
        if filename == "views.py" and parsed["functions"]:
            view_funcs = [f for f in parsed["functions"] if not f["name"].startswith("_")]
            lines.extend(render_functions(view_funcs))
        elif filename != "views.py" and parsed["functions"]:
            mod_funcs = [f for f in parsed["functions"] if not f["name"].startswith("_")]
            if mod_funcs:
                lines.extend(render_functions(mod_funcs, "模块级函数"))

    routes = find_url_routes(app)
    if routes:
        lines.append("### 路由 (`urls.py`)")
        lines.append("")
        lines.append("| 路径 | 视图 |")
        lines.append("|------|------|")
        for path, view in routes:
            lines.append(f"| `{path}` | `{view}` |")
        lines.append("")

    extra_files = []
    if app == "operations":
        for name in ["acceptance_service.py", "acceptance_events.py"]:
            p = app_dir / name
            if p.exists():
                extra_files.append(p)
    for path in extra_files:
        parsed = parse_py_file(path)
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"### 附加模块 (`{rel}`)")
        lines.append("")
        for cls in parsed["classes"]:
            lines.extend(render_class(cls))

    return lines


def build_mermaid_flow() -> str:
    return """```mermaid
stateDiagram-v2
    [*] --> queuing: 提交充电请求
    queuing --> dispatched: 调度派桩
    dispatched --> charging: 队首开始充电
    charging --> completed: 正常结束
    charging --> cancelled: 用户取消
    queuing --> cancelled: 取消排队
    dispatched --> cancelled: 取消排队
    charging --> pending_reschedule: 桩故障
    dispatched --> pending_reschedule: 桩故障
    pending_reschedule --> dispatched: 重调度成功
```"""


def generate() -> str:
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines = [
        "# 后端架构参考手册",
        "",
        "> **自动生成文档** — 请勿直接手工编辑正文结构部分。",
        f"> 最后生成时间：`{now}`",
        "",
        "## 文档维护规则",
        "",
        "### 自动更新（推荐）",
        "",
        "修改 `backend/apps/` 下 models、services、views 后，在项目根目录执行：",
        "",
        "```bash",
        "python backend/scripts/generate_backend_docs.py",
        "```",
        "",
        "CI 校验（确保文档与代码同步）：",
        "",
        "```bash",
        "python backend/scripts/generate_backend_docs.py --check",
        "```",
        "",
        "### 需手工同步的内容",
        "",
        "| 变更类型 | 更新位置 |",
        "|----------|----------|",
        "| 新增/删除 App | 修改 `generate_backend_docs.py` 中 `APP_ORDER` |",
        "| 业务逻辑说明、状态机描述 | 修改 `generate_backend_docs.py` 中 `MANUAL_BUSINESS` |",
        "| API 入参/出参详情 | 更新 `docs/API接口文档.md` |",
        "| 枚举常量语义 | 改 `common/enums.py` 后重新运行生成脚本 |",
        "",
        "### 建议触发更新的时机",
        "",
        "- 新增 Model 字段或 Service 公开方法",
        "- 修改 View 路由或鉴权装饰器",
        "- 调整调度/计费/故障核心业务逻辑",
        "- 合并 PR 前运行 `--check` 防止文档漂移",
        "",
        "---",
        "",
        "## 应用总览",
        "",
        "| App | 路径 | 职责 |",
        "|-----|------|------|",
        "| common | `apps/common/` | 枚举、鉴权、响应、工具、模拟时钟 |",
        "| accounts | `apps/accounts/` | 注册登录、用户/车辆 |",
        "| station | `apps/station/` | 充电站、配置、充电桩 |",
        "| charging | `apps/charging/` | 充电请求、队列、调度、会话 |",
        "| billing | `apps/billing/` | 分时计费、账单 |",
        "| operations | `apps/operations/` | 故障、报表、验收 |",
        "",
        "## 核心状态流转",
        "",
        build_mermaid_flow(),
        "",
        "---",
        "",
    ]

    for app in APP_ORDER:
        lines.extend(render_app_section(app))

    lines.append("## 模块依赖关系")
    lines.append("")
    lines.append("```")
    lines.append("views → services → models")
    lines.append("charging.services → station.services, accounts.services, billing.services")
    lines.append("operations.services → charging.services, station.services, billing.models")
    lines.append("所有业务时间 → common.sim_clock.system_now()")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成后端架构参考手册")
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查已生成文档是否与当前代码一致，不一致则退出码 1",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help=f"输出路径（默认 {OUTPUT}）",
    )
    args = parser.parse_args()

    content = generate()

    if args.check:
        if not args.output.exists():
            print(f"文档不存在: {args.output}", file=sys.stderr)
            sys.exit(1)
        existing = args.output.read_text(encoding="utf-8")
        # 忽略时间戳行差异
        def strip_timestamp(text: str) -> str:
            return "\n".join(
                line for line in text.splitlines()
                if not line.startswith("> 最后生成时间：")
            )

        if strip_timestamp(existing) != strip_timestamp(content):
            print("文档与代码不同步，请运行: python backend/scripts/generate_backend_docs.py", file=sys.stderr)
            sys.exit(1)
        print("文档与代码同步。")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"已生成: {args.output}")


if __name__ == "__main__":
    main()
