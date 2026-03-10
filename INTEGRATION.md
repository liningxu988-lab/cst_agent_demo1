# Phase 1 与现有代码衔接说明

## 第一阶段目录结构

```
cst_agent_demo/
├── tools/
│   ├── __init__.py
│   ├── base.py              # ToolResult, BaseTool
│   ├── registry.py           # ToolRegistry
│   ├── cst_context.py        # 控制器上下文（注入/获取）
│   ├── cst_project_tools.py  # open_project
│   ├── cst_param_tools.py    # set_parameter
│   ├── cst_solver_tools.py   # run_solver
│   └── cst_result_tools.py   # read_s11
├── state/
│   ├── __init__.py
│   ├── models.py        # RunState, IterationState
│   └── state_store.py   # StateStore
├── domain/
│   ├── __init__.py
│   └── task_models.py   # DesignTask, AgentDecision
├── run_state/           # 状态持久化目录
├── scripts/             # 原有 CST 脚本（不修改）
├── cst_runner.py        # 原有主程序（不修改）
└── INTEGRATION.md       # 本文件
```

## 与 cst_runner.py 的衔接

### 当前 cst_runner.py 流程

1. `load_params_from_cli()` → 参数
2. `CSTController` / `CSTPythonAPIController` 等 → 仿真
3. `DeepSeekClient` → AI 分析
4. 循环：参数 → 仿真 → 读结果 → AI → 更新参数

### 适配方式（新增适配层，不修改 cst_runner.py）

1. **状态持久化**：在 `cst_runner.py` 主循环中，每次迭代前后调用 `StateStore.save()`，将当前 `params`、`targets`、迭代次数、阶段写入 `run_state/{run_id}.json`。
2. **工具封装**：将 `CSTController.run_simulation()`、`ai_client.analyze()` 等封装为继承 `BaseTool` 的适配器，内部调用原有逻辑，对外返回 `ToolResult`。
3. **结构化决策**：AI 返回的文本由解析层转为 `AgentDecision`（如 `action="update_params"`, `params={...}`），再驱动执行。

### 示例：在 cst_runner 中接入 StateStore（新增代码）

```python
# 在 cst_runner.py 顶部新增导入（不修改原有逻辑）
from state import get_state_store, RunState, RunPhase

# 主循环开始前
store = get_state_store()
run_id = f"run_{int(time.time())}"
state = RunState(run_id=run_id, phase=RunPhase.INIT, params=params, targets=targets)
store.save(state)

# 每次迭代后
state.phase = RunPhase.PARAM_UPDATE
state.current_iteration = i
store.save(state)
```

## 与 scripts/ 的衔接

### 工具适配器示例（新增文件，不修改 scripts/）

```python
# tools/adapters/cst_sim_tool.py（第二阶段实现）
from tools.base import BaseTool, ToolResult, ToolStatus

class CSTSimTool(BaseTool):
    name = "cst_run_simulation"

    def run(self, params: dict, **kwargs) -> ToolResult:
        from scripts.cst_controller import CSTController  # 复用旧代码
        try:
            ctrl = CSTController()
            ctrl.connect()
            result = ctrl.run_simulation(params)  # 原有逻辑
            return ToolResult(status=ToolStatus.SUCCESS, tool_name=self.name, data=result)
        except Exception as e:
            return ToolResult(status=ToolStatus.FAILED, tool_name=self.name, error=str(e))
```

### 现有 scripts 职责保持不变

| 文件 | 职责 | 新框架中的角色 |
|------|------|----------------|
| cst_controller.py | CST COM 控制 | 被 CSTSimTool 等适配器调用 |
| ai_client.py | DeepSeek API | 被 AIAnalyzeTool 适配器调用 |
| structure_builder.py | 结构建模 | 被 StructureBuildTool 适配器调用 |
| cst_python_api_controller.py | Python API 控制 | 同上，可选适配 |

## 数据流示意

```
[参数文件] → DesignTask (domain)
     ↓
[Agent 决策] → AgentDecision (domain)
     ↓
[工具执行] → BaseTool.run() → ToolResult (tools)
     ↓
[状态更新] → RunState (state) → run_state/*.json
```

## 中断恢复

- 启动时检查 `run_state/` 下是否有未完成的 `run_id`。
- 若有，`StateStore.load(run_id)` 恢复 `RunState`，从 `current_iteration` 和 `phase` 继续执行。

---

## Tool 适配层

### 旧代码复用方案

| 工具 | 复用旧脚本 | 旧接口 |
|------|------------|--------|
| open_project | cst_controller / cst_python_api_controller | `ctrl.open_project(project_path)` |
| set_parameter | 同上 | `ctrl.set_parameters(params)` |
| run_solver | 同上 | `ctrl.run_simulation(wait_complete, timeout)` |
| read_s11 | 同上 | `ctrl.get_s11_parameters()` 或 `ctrl.get_s_parameters_full()` |

### 调用链：Agent -> ToolRegistry -> Tool -> 旧脚本

```
Agent 决策 (AgentDecision)
    ↓
ToolRegistry.run("open_project", project_path="...")
    ↓
OpenProjectTool.run(project_path=...)
    ↓
get_controller().open_project(project_path)   # 复用 scripts/cst_controller.py
    ↓
ToolResult(status, message, data)
```

### 使用方式

```python
# 1. 启动时注入控制器
from tools.cst_context import set_controller
from cst_runner import init_cst_controller, load_config

config = load_config()
ctrl = init_cst_controller(config)
ctrl.connect()
set_controller(ctrl)

# 2. 通过 Registry 调用工具
from tools.registry import get_registry

reg = get_registry()
r1 = reg.run("open_project", project_path="templates/antenna_template.cst")
r2 = reg.run("set_parameter", params={"patch_length": 12.0})
r3 = reg.run("run_solver", wait_complete=True)
r4 = reg.run("read_s11")
```
