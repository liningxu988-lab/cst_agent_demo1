"""
Skill 调用示例。
"""

from tools import get_registry, set_controller
from scripts.cst_controller import FakeCSTController
from skills import load_all_skills, get_skill_by_scenario


def main():
    # 1. 注入控制器
    ctrl = FakeCSTController()
    ctrl.connect()
    set_controller(ctrl)

    # 2. 加载所有 Skill
    skills = load_all_skills()
    print("已加载 Skill:", list(skills.keys()))

    # 3. 调用 unit_cell_builder
    reg = get_registry()
    ctx = {"tool_registry": reg}
    builder = skills.get("unit_cell_builder")
    if builder:
        print("\n--- Unit Cell Builder ---")
        print("tools:", builder.tools)
        print("scenarios:", builder.scenarios)
        r = builder.run(ctx, project_path="test.cst", structure_plan={"params": {"patch_length": 12.0, "patch_width": 10.0}})
        print("result:", r)

    # 4. 调用 sparam_optimizer
    optimizer = skills.get("sparam_optimizer")
    if optimizer:
        print("\n--- S-Parameter Optimizer ---")
        print("tools:", optimizer.tools)
        r = optimizer.run(ctx, params={"patch_length": 12.0, "patch_width": 10.0}, targets={"freq_min_GHz": 2.4, "freq_max_GHz": 2.5, "s11_max_dB": -10.0})
        print("result:", r)

    # 5. 按场景查找
    skill = get_skill_by_scenario(skills, "s11_optimization")
    print("\n按场景 s11_optimization 查找:", skill.name if skill else None)


if __name__ == "__main__":
    main()
