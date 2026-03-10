"""
最小 Agent 运行示例。
使用 FakeCSTController，无需真实 CST 即可验证主循环。
"""

import time

from tools import set_controller, get_registry
from scripts.cst_controller import FakeCSTController
from agent import Orchestrator


def main():
    # 1. 注入假控制器（无需真实 CST）
    ctrl = FakeCSTController()
    ctrl.connect()
    set_controller(ctrl)

    # 2. 确保工具已注册
    reg = get_registry()
    print("已注册工具:", reg.list_tools())

    # 3. 创建编排器并运行
    orch = Orchestrator()
    result = orch.run(
        task_id=f"run_{int(time.time())}",
        project_path="templates/antenna_template.cst",
        initial_params={"patch_length": 12.0, "patch_width": 10.0},
        targets={
            "freq_min_GHz": 2.4,
            "freq_max_GHz": 2.5,
            "s11_max_dB": -10.0,
        },
        max_iterations=3,
        resume=False,
    )

    print("\n" + "=" * 60)
    print("运行结果")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
