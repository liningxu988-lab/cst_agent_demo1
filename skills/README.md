# Skills 插件

领域能力以 Skill 插件形式组织，复用已有 tools。

## 新增文件

| 文件 | 职责 |
|------|------|
| **base_skill.py** | Skill 基类，定义 meta、load_prompt、load_schemas、run |
| **skill_loader.py** | 从目录加载 Skill，按场景查找 |
| **unit_cell_builder/** | 反射单元结构构建 Skill |
| **sparam_optimizer/** | S 参数优化 Skill |

## Skill 结构

每个 Skill 目录需含：

- **skill.py** - 实现类，继承 BaseSkill
- **prompt.md** - 说明与 prompt
- **schemas.json** - 输入输出 schema

## Skill 声明

- name
- description
- tools（可调用工具列表）
- scenarios（适用场景）

## 调用示例

```python
from tools import get_registry, set_controller
from skills import load_all_skills, get_skill_by_scenario

set_controller(your_controller)
skills = load_all_skills()
ctx = {"tool_registry": get_registry()}

# 按名称
builder = skills["unit_cell_builder"]
r = builder.run(ctx, project_path="x.cst", structure_plan={"params": {...}})

# 按场景
skill = get_skill_by_scenario(skills, "s11_optimization")
```

## 预留扩展

- phase_sweep
- structure_switcher
