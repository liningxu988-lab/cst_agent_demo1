# run_state 目录使用说明

本目录用于存储 CST 单元优化任务的状态，支持**多轮迭代记录**与**中断恢复**。

## 目录结构

```
run_state/
├── README.md              # 本说明
├── active_task.json       # 当前活动任务（主入口，用于恢复）
├── active_task.example.json  # 示例结构（参考用，不参与运行）
├── {task_id}.json         # 按任务 ID 持久化的完整状态
└── .gitkeep
```

## 文件说明

### active_task.json

当前活动任务的完整状态。系统启动时优先读取此文件以支持中断恢复。

- **存在且 phase 非 done/failed**：视为未完成任务，可从 `current_iteration` 继续
- **不存在**：无活动任务，需调用 `init_task` 初始化

### {task_id}.json

按 `task_id` 命名的任务状态副本，与 `active_task.json` 内容一致（同一任务会同时写入两处），便于按 ID 查询历史任务。

## 状态模型

| 模型 | 说明 |
|------|------|
| **TaskState** | 完整任务状态：task_id、phase、current_params、targets、iteration_records、best_result |
| **IterationRecord** | 单轮迭代：params、result_snapshot、evaluation、ai_decision |
| **BestResultSummary** | 最佳结果摘要：s11_min_dB、freq_at_min_GHz、params、iteration |

## 使用流程

### 1. 初始化任务

```python
from state import get_state_store

store = get_state_store()
task = store.init_task(
    task_id="run_001",
    project_path="templates/antenna_template.cst",
    initial_params={"patch_length": 12.0, "patch_width": 10.0},
    targets={"freq_min_GHz": 2.4, "freq_max_GHz": 2.5, "s11_max_dB": -10.0},
    max_iterations=10,
)
```

### 2. 保存每轮迭代

```python
store.save_iteration_record(
    task_id="run_001",
    iteration=1,
    params={"patch_length": 11.5},
    result_snapshot={"success": True, "results": {...}, "errors": []},
    evaluation={"s_params_ok": True, "all_ok": False, "details": {...}},
    ai_decision={"parameter_plan": {"changes": {...}}},
)
```

### 3. 保存最佳结果

```python
store.save_best_result(
    task_id="run_001",
    iteration=1,
    params={"patch_length": 11.5},
    s11_min_dB=-12.3,
    freq_at_min_GHz=2.45,
    bandwidth_10dB_MHz=80.0,
    all_ok=False,
)
```

### 4. 读取活动任务（中断恢复）

```python
task = store.get_active_task()
if task and task.phase not in ("done", "failed"):
    # 从 task.current_iteration 继续
    # 使用 task.current_params 作为下一轮起点
    # 使用 task.best_result 获取当前最优
    ...
```

### 5. 标记完成

```python
store.mark_task_done(task_id="run_001", success=True)
```

## 中断恢复逻辑

1. 启动时调用 `get_active_task()`
2. 若返回 `None`：无未完成任务，按正常流程 `init_task` 启动
3. 若返回 `TaskState` 且 `phase` 非 `done`/`failed`：
   - 使用 `current_params` 作为下一轮参数
   - 从 `current_iteration + 1` 继续循环
   - 参考 `best_result` 判断是否已达标

## 与 cst_runner 的兼容

`IterationRecord` 与 `cst_runner.run_design_iteration` 返回的 `iteration_record` 结构兼容：

- `params`：当前参数
- `result_snapshot`：`collect_result_snapshot` 的返回值
- `evaluation`：`evaluate_design` 的返回值
- `ai_decision`：AI 分析结果（可选）

可直接将 `run_design_iteration` 的 `iteration_record` 传入 `save_iteration_record`。
