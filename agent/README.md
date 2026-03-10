# Agent 模块

最小可运行的 Agent 主循环，采用 **plan -> execute -> evaluate -> persist** 模式。

## 文件职责

| 文件 | 职责 |
|------|------|
| **planner.py** | 生成结构化 ActionPlan，不直接执行工具 |
| **executor.py** | 按计划调用 ToolRegistry 执行工具 |
| **evaluator.py** | 分析执行结果，基于目标频点和 S11 评分 |
| **stop_policy.py** | 判断是否停止迭代 |
| **orchestrator.py** | 串起完整流程 |
| **models.py** | Action、ActionPlan、EvaluationResult 等结构化模型 |

## 主循环

```
plan -> execute -> evaluate -> persist
  ↓        ↓          ↓           ↓
Planner  Executor  Evaluator  StateStore
```

## 支持动作（第一版）

- `open_project`
- `set_parameter`
- `run_solver`
- `read_s11`

## 最小运行示例

```bash
python run_agent_minimal.py
```

使用 FakeCSTController，无需真实 CST 即可验证主循环。

## 使用方式

```python
from tools import set_controller
from agent import Orchestrator

# 1. 注入 CST 控制器
set_controller(your_cst_controller)

# 2. 运行
orch = Orchestrator()
result = orch.run(
    task_id="run_001",
    project_path="templates/antenna_template.cst",
    initial_params={"patch_length": 12.0, "patch_width": 10.0},
    targets={"freq_min_GHz": 2.4, "freq_max_GHz": 2.5, "s11_max_dB": -10.0},
    max_iterations=10,
)
```
