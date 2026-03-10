# LLM 模块

规范 LLM 输出格式，让 AI 决策变成结构化 ActionPlan，禁止自由文本直接驱动执行。

## 新增文件

| 文件 | 职责 |
|------|------|
| **models.py** | LLMActionPlan、LLMEvaluationResult 等结构化模型 |
| **json_repair.py** | JSON 轻量修复（markdown 剥离、尾随逗号、控制字符） |
| **response_parser.py** | 解析 LLM 输出为 LLMActionPlan，兼容旧 ai_client 格式 |
| **message_builder.py** | 构建 system/user 消息，约束输出 JSON |
| **client.py** | LLM 调用封装，与 DeepSeek 兼容 |
| **adapters.py** | 将旧 ai_client 接入新流程的适配器 |
| **prompts/planner_system.txt** | planner 系统 prompt 示例 |

## 数据模型

### LLMActionPlan
```python
stop: bool
reason: str
actions: List[LLMAction]  # {"tool": str, "kwargs": dict}
parameter_changes: Dict[str, float]
```

### LLMEvaluationResult
```python
score: float
all_ok: bool
s11_min_dB: float
freq_at_min_GHz: float
stop: bool
reason: str
next_params: Dict[str, float]
details: Dict
```

## JSON 解析与修复

- `parse_json(raw)`：解析失败时自动调用 `repair_json` 重试
- `repair_json(raw)`：去除 markdown、尾随逗号、控制字符
- `validate_action_plan(d)`：补全缺失字段，过滤非法 action

## 与 ai_client 兼容

```python
# 适配器方式接入旧 DeepSeekClient
from scripts.ai_client import DeepSeekClient
from llm.adapters import DeepSeekToLLMAdapter

adapter = DeepSeekToLLMAdapter(DeepSeekClient())
plan = adapter.plan_for_design(design_task, params, results, history)
# plan 为 LLMActionPlan，可转 ActionPlan 供 executor 执行
```

## 使用新 LLMClient

```python
from llm import LLMClient, create_from_config

client = create_from_config(config)
actions = client.plan_for_design(goals, params, results, history)
```
