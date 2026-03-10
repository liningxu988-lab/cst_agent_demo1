# 自由度提升设计说明

## 目标

在结构化状态和结构化动作约束下，提升 AI 决策自由度，避免固定流程脚本感。

## 策略类型（结构化）

| 策略 | 含义 | 动作序列 |
|------|------|----------|
| continue_tune | 继续微调参数 | set_parameter -> run_solver -> read_s11 |
| switch_structure | 切换结构类型 | set_parameter(新结构) -> run_solver -> read_s11 |
| param_sweep | 参数扫描 | 多组 set_parameter -> run_solver -> read_s11（预留） |
| stop_route | 停止当前路线 | 无动作，触发换路线或结束 |

## TaskState 扩展

- **tried_actions**: 已尝试的动作摘要（避免重复）
- **failed_actions**: 失败动作记录（避免重试无效路径）
- **best_route**: 当前最佳路线 {structure_type, params, score}
- **current_hypothesis**: 当前假设 {route, structure_type}

## Evaluator 扩展

- **no_improvement_count**: 连续无改善轮数
- **suggest_route_change**: 是否建议换路线（无改善达 3 轮时）

## StopPolicy 扩展

- **switch_route**: 换路线而非直接停止
- **next_route**: 建议的下一条路线（如 switch_structure）

## 流程

1. Planner 根据 suggest_route_change、no_improvement_count、current_hypothesis 选择 route
2. Executor 执行对应 actions
3. Evaluator 计算 score，检测无改善，设置 suggest_route_change
4. StopPolicy.decide() 返回 switch_route 或 should_stop
5. Orchestrator 在 switch_route 时更新 current_hypothesis，继续下一轮

## 约束

- 所有决策输出为结构化枚举/JSON
- 禁止自由文本直接驱动底层执行
