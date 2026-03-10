"""
Kiko - CST 反射单元建模 AI 助手
启动后进入交互模式，用自然语言描述需求，Kiko 调用 CST 进行建模与仿真。
"""

import json
import sys
from pathlib import Path

# 确保项目根在 path 中
sys.path.insert(0, str(Path(__file__).parent))

from cst_runner import (
    load_config,
    init_ai_client,
    init_cst_controller,
    build_design_task,
    run_automatic_design,
    run_design_iteration,
    collect_result_snapshot,
    evaluate_design,
)
from scripts.kiko_ai import KikoAI, S_PARAM_HINTS


def main():
    print("\n" + "=" * 60)
    print("  Kiko - CST 反射单元建模助手")
    print("=" * 60)
    print("\n用自然语言描述你的需求，例如：")
    print("  - 「我想设计 2.45GHz 的反射单元，贴片 12x10mm」")
    print("  - 「中心频率 3GHz，贴片尺寸 15x12」")
    print("  - 「请仿真并给出 S11 结果」")
    print("\n提示：若未指定频率，我会提醒你输入。")
    print("输入 'quit' 或 'exit' 退出。")
    print("=" * 60)

    config = load_config()
    kiko_ai = KikoAI(
        api_key=config.get("deepseek_api_key"),
        base_url=config.get("deepseek_base_url", "https://api.deepseek.com"),
        model=config.get("deepseek_model", "deepseek-chat"),
    )
    ai_client = init_ai_client(config)
    cst_ctrl = init_cst_controller(config)

    project_path = "templates/antenna_template"
    design_task = None
    current_params = {}
    freq_center = None
    freq_min = 2.4
    freq_max = 2.5
    history = []

    # 打开项目
    if not cst_ctrl.open_project(project_path):
        print("[Kiko] 无法打开模板项目，将使用模拟模式运行。")
    else:
        if hasattr(cst_ctrl, "set_design_targets"):
            cst_ctrl.set_design_targets({"freq_min_GHz": freq_min, "freq_max_GHz": freq_max})

    try:
        while True:
            try:
                user_input = input("\n你 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("再见！")
                break

            # 解析用户意图
            context = {
                "freq_center_GHz": freq_center,
                "current_params": current_params,
                "history_len": len(history),
            }
            parsed = kiko_ai.parse_user_intent(user_input, context)

            # 若需要频率，提醒用户
            if parsed.get("need_freq"):
                print(f"\nKiko > {parsed.get('reply', '请提供中心频率（GHz），例如 2.45')}")
                continue

            # 更新频率
            fc = parsed.get("freq_center_GHz")
            if fc is not None:
                freq_center = fc
                freq_min = parsed.get("freq_min_GHz", freq_center - 0.05)
                freq_max = parsed.get("freq_max_GHz", freq_center + 0.05)

            # 更新参数
            params = parsed.get("params") or {}
            for k, v in params.items():
                if isinstance(v, (int, float)):
                    current_params[k] = v

            # 更新 structure_plan
            structure_plan = parsed.get("structure_plan") or {}
            if structure_plan.get("structure_type"):
                for k, v in (structure_plan.get("params") or {}).items():
                    if isinstance(v, (int, float)):
                        current_params[k] = v

            # 若仍无频率，用默认
            if freq_center is None:
                freq_center = 2.45
                freq_min, freq_max = 2.4, 2.5

            if not current_params:
                current_params = {"patch_length": 12.0, "patch_width": 10.0}

            # 构建 design_task
            params_for_task = {
                "project_path": project_path,
                **current_params,
                "targets": {
                    "freq_min_GHz": freq_min,
                    "freq_max_GHz": freq_max,
                    "s11_max_dB": -10.0,
                },
                "structure_plan": structure_plan,
            }
            design_task = build_design_task(params_for_task, config)

            # 应用 structure_plan（若 AI 指定了三层等结构）
            if structure_plan.get("structure_type") and hasattr(cst_ctrl, "apply_structure_plan"):
                cst_ctrl.apply_structure_plan(structure_plan)

            # 应用 Kiko 固定建模条件
            if hasattr(cst_ctrl, "apply_kiko_setup"):
                ok = cst_ctrl.apply_kiko_setup(freq_center, freq_min, freq_max)
                if not ok:
                    print("[Kiko] 建模条件应用失败，继续尝试仿真...")

            # 回复用户
            print(f"\nKiko > {parsed.get('reply', '')}")
            print(f"      频率: {freq_min}-{freq_max} GHz，参数: {current_params}")

            # 用户说「优化」时，启动完整优化循环
            if parsed.get("intent") == "optimize" or "优化" in user_input or "继续" in user_input:
                print("\n[Kiko] 启动 AI 自动优化循环...")
                if hasattr(cst_ctrl, "apply_kiko_setup"):
                    cst_ctrl.apply_kiko_setup(freq_center, freq_min, freq_max)
                result = run_automatic_design(
                    cst_ctrl=cst_ctrl,
                    ai_client=ai_client,
                    design_task=design_task,
                    initial_params=current_params,
                    max_iterations=config.get("design_settings", {}).get("max_iterations", 10),
                    project_path=project_path,
                )
                if result.get("success"):
                    current_params = result.get("final_params", current_params)
                    s_summary = (result.get("final_results", {}).get("s_params", {}) or {}).get("summary", {})
                    print(f"\nKiko > 优化完成！最终 S11: {s_summary.get('s11_min_dB', 'N/A')} dB @ {s_summary.get('freq_at_min_GHz', 'N/A')} GHz")
                else:
                    print(f"\nKiko > 优化未完全成功: {result.get('error', result.get('message', '未知'))}")
                continue

            # 运行一次迭代：设置参数 -> 仿真 -> 读结果
            params_to_set = {k: v for k, v in current_params.items() if isinstance(v, (int, float)) and not k.startswith("_")}
            print("\n[Kiko] 正在设置参数并运行仿真...")
            if hasattr(cst_ctrl, "set_result_channels"):
                cst_ctrl.set_result_channels(["s_params"])
            if not cst_ctrl.set_parameters(params_to_set):
                print("[Kiko] 参数设置失败")
                continue
            if hasattr(cst_ctrl, "set_design_targets"):
                cst_ctrl.set_design_targets({"freq_min_GHz": freq_min, "freq_max_GHz": freq_max})
            if not cst_ctrl.run_simulation(wait_complete=True):
                print("[Kiko] 仿真失败（将触发 AI 错误接管若已启用）")
                # 可在此调用 _handle_cst_error 等
                continue

            snapshot = collect_result_snapshot(cst_ctrl, ["s_params"])
            results = snapshot.get("results", {})
            evaluation = evaluate_design(results, design_task)
            history.append({
                "params": current_params.copy(),
                "result_snapshot": snapshot,
                "evaluation": evaluation,
            })

            # 用 Kiko AI 解释 S 参数
            explain = kiko_ai.explain_s_params({"s_params": results.get("s_params", {})})
            print(f"\nKiko > {explain}")

            if evaluation.get("all_ok"):
                print("\nKiko > 设计已满足目标！需要继续优化或调整吗？")
            else:
                print("\nKiko > 当前未达标，输入「优化」或「继续」将启动 AI 自动调参；或直接描述新的参数需求。")

    finally:
        cst_ctrl.close()


if __name__ == "__main__":
    main()
