"""
CST 自动设计主程序
实现：参数设置 -> 仿真运行 -> S11读取 -> AI分析 -> 参数调整的自动循环
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 导入自定义模块
from scripts.ai_client import DeepSeekClient
from scripts.cst_controller import CSTController, FakeCSTController
from scripts.cst_file_controller import CSTFileController
from scripts.cst_auto_macro_controller import CSTAutoMacroController
from scripts.cst_batch_controller import CSTBatchController
from scripts.cst_fully_auto import CSTFullyAutoController
from scripts.cst_python_api_controller import CSTPythonAPIController
from scripts.fake_ai_client import FakeDeepSeekClient
from scripts.cst_bridge import run_cst_simulation


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.json"

    default_config = {
        "deepseek_api_key": "",
        "deepseek_model": "deepseek-chat",
        "deepseek_base_url": "https://api.deepseek.com",
        "cst_settings": {
            "auto_find_cst": True,
            "cst_exe_path": "",
            "ai_role_profile": "你是一个天线与电磁领域的专家，具有充足的电磁仿真经验以及CST软件的建模与仿真使经验，擅长超表面，天线罩，天线的设计与调参。",
            "enabled_result_channels": ["s_params", "radiation"],
            "strict_result_required": True,
            "radiation_mapping": {
                "preferred_tree_paths": [],
                "primary_metric": "peak_gain_dBi",
                "axis_unit": "deg",
                "fallback_keywords": ["farfield", "far field", "gain", "directivity", "radiation", "pattern"],
            },
            "use_fake_controller": False,
            "simulation_timeout": 600,
        },
        "design_settings": {
            "max_iterations": 10,
            "convergence_threshold": 0.1,
            "auto_save": True,
            "output_dir": "outputs",
        },
    }

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            # 合并默认配置
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    else:
        print(f"警告: 未找到配置文件 {config_path}，使用默认配置")
        return default_config


def load_params_from_cli() -> Tuple[Path, Dict[str, Any]]:
    """从命令行加载参数文件"""
    if len(sys.argv) < 2:
        print("用法: python cst_runner.py <参数文件.json>")
        print("\n参数文件示例:")
        print(json.dumps({
            "patch_length": 12.0,
            "patch_width": 10.0,
            "targets": {
                "freq_min_GHz": 2.4,
                "freq_max_GHz": 2.5,
                "s11_max_dB": -10.0
            }
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    params_path = Path(sys.argv[1])

    if not params_path.exists():
        print(f"错误: 参数文件不存在 -> {params_path}")
        sys.exit(1)

    with open(params_path, "r", encoding="utf-8") as f:
        params = json.load(f)

    return params_path, params


def init_ai_client(config: Dict[str, Any]):
    """初始化 AI 客户端"""
    api_key = config.get("deepseek_api_key", "")
    model = config.get("deepseek_model", "deepseek-chat")
    base_url = config.get("deepseek_base_url", "https://api.deepseek.com")

    if not api_key or api_key == "your-api-key-here":
        print("[注意] 未配置 DeepSeek API Key，使用模拟 AI 客户端")
        return FakeDeepSeekClient()

    return DeepSeekClient(api_key=api_key, model=model, base_url=base_url)


def init_cst_controller(config: Dict[str, Any]):
    """初始化 CST 控制器 - 按优先级尝试不同模式"""
    cst_settings = config.get("cst_settings", {})

    # 使用假控制器（测试模式）
    if cst_settings.get("use_fake_controller", False):
        print("[Mode] Using FakeCSTController (test mode, no real CST)")
        return FakeCSTController()

    # 获取指定的控制器模式
    controller_mode = cst_settings.get("controller_mode", "auto")

    # 模式 1: Python API 模式（100% 全自动，无需任何人工介入）
    if controller_mode in ["auto", "python_api"]:
        try:
            controller = CSTPythonAPIController(
                preferred_s11_tree_path=cst_settings.get("preferred_s11_tree_path", ""),
                allow_proxy_curve=bool(cst_settings.get("allow_proxy_curve", False)),
                radiation_mapping=cst_settings.get("radiation_mapping", {}),
            )
            if controller._setup_python_path() and controller.connect():
                print("[Mode] Using CSTPythonAPIController (Official Python API)")
                print("       100% FULLY AUTOMATIC - Zero human intervention!")
                return controller
            else:
                if controller_mode == "python_api":
                    print("[Info] Python API connect failed after wrapper+low-level attempts.")
                    print("       Auto-fallback to fully_auto mode (no Python API needed)...")
                    controller_mode = "fully_auto"  # fallback
                else:
                    print("[Info] Python API not available, trying other modes...")
        except RuntimeError as re:
            if "Python API" in str(re):
                print("[Info] Auto-fallback to fully_auto mode...")
                controller_mode = "fully_auto"
            else:
                raise
        except Exception as e:
            if controller_mode == "python_api":
                raise
            print(f"[Info] Python API controller failed: {e}")
            print("         Trying other modes...")

    # 模式 2: 完全全自动模式（命令行启动，自动执行，零点击）
    if controller_mode in ["auto", "fully_auto", "full_auto", "zero_click"]:
        try:
            controller = CSTFullyAutoController()
            if controller.connect():
                print("[Mode] Using CSTFullyAutoController (ZERO-CLICK mode)")
                print("       100% FULLY AUTOMATIC - No human intervention!")
                print("       Auto-starts CST with embedded auto-execution macro")
                return controller
            else:
                if controller_mode in ["fully_auto", "full_auto", "zero_click"]:
                    raise RuntimeError("CST not found for fully-auto mode")
        except Exception as e:
            if controller_mode in ["fully_auto", "full_auto", "zero_click"]:
                raise
            print(f"[Info] Fully-auto controller failed: {e}")
            print("         Trying batch mode...")

    # 模式 3: 批处理模式（全自动，通过脚本启动 CST）
    if controller_mode in ["auto", "batch", "batch_mode"]:
        try:
            controller = CSTBatchController()
            if controller.connect():
                print("[Mode] Using CSTBatchController (Batch mode)")
                print("       Auto-starts CST, but may need CST security settings")
                return controller
            else:
                if controller_mode == "batch":
                    raise RuntimeError("CST not found for batch mode")
        except Exception as e:
            if controller_mode == "batch":
                raise
            print(f"[Info] Batch controller failed: {e}")
            print("         Trying auto-macro mode...")

    # 模式 4: 自动宏模式（一键完成所有操作）
    if controller_mode in ["auto", "auto_macro", "macro"]:
        try:
            controller = CSTAutoMacroController()
            print("[Mode] Using CSTAutoMacroController (One-click mode)")
            print("       Requires 1 click per iteration")
            return controller
        except Exception as e:
            if controller_mode in ["auto_macro", "macro"]:
                raise
            print(f"[Info] Auto-macro controller failed: {e}")
            print("         Trying standard file mode...")

    # 模式 5: 标准文件交换模式（分步手动操作）
    if controller_mode in ["auto", "file"]:
        cst_exe = cst_settings.get("cst_exe_path", "")
        controller = CSTFileController(cst_exe_path=cst_exe)
        print("[Mode] Using CSTFileController (Manual step-by-step)")
        print("       Generates separate VBA macros for each step")
        return controller

    # 模式 6: COM 接口（可能不稳定）
    if controller_mode == "com":
        cst_exe = cst_settings.get("cst_exe_path", "")
        if cst_settings.get("auto_find_cst", True) and not cst_exe:
            cst_exe = None

        try:
            controller = CSTController(cst_exe_path=cst_exe)
            print("[Mode] Using CSTController (COM interface)")
            return controller
        except Exception as e:
            print(f"[Warning] COM controller failed: {e}")
            print("         Falling back to file mode")
            return CSTFileController()

    # 默认回退到完全全自动模式
    return CSTFullyAutoController()


def evaluate_s11(s11_data: Dict[str, Any], targets: Dict[str, float]) -> Dict[str, Any]:
    """
    评估 S11 结果是否满足目标要求

    Returns:
        {
            "s11_ok": bool,  # S11 是否达标
            "freq_ok": bool,  # 频率是否达标
            "all_ok": bool,  # 全部达标
            "details": dict,  # 详细评估
        }
    """
    s11_min = s11_data.get("s11_min_dB", -999)
    freq_at_min = s11_data.get("freq_at_min_GHz", 0)
    bandwidth = s11_data.get("bandwidth_10dB_MHz", 0)

    freq_min = targets.get("freq_min_GHz", 2.4)
    freq_max = targets.get("freq_max_GHz", 2.5)
    s11_threshold = targets.get("s11_max_dB", -10.0)

    # 评估
    s11_ok = s11_min <= s11_threshold
    freq_ok = freq_min <= freq_at_min <= freq_max
    all_ok = s11_ok and freq_ok

    return {
        "s11_ok": s11_ok,
        "freq_ok": freq_ok,
        "all_ok": all_ok,
        "details": {
            "s11_min_dB": s11_min,
            "s11_threshold": s11_threshold,
            "freq_at_min_GHz": freq_at_min,
            "target_freq_range": [freq_min, freq_max],
            "bandwidth_10dB_MHz": bandwidth,
        },
    }


def build_design_task(params: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """构建统一 design_task 协议。"""
    targets = params.get("targets", {})
    cst_settings = config.get("cst_settings", {})

    result_channels = ["s_params"]

    adjustable_params = {
        k: v for k, v in params.items()
        if isinstance(v, (int, float)) and k not in ["targets"]
    }
    param_bounds = params.get("parameter_bounds", {})
    structure_plan = params.get("structure_plan", {})

    return {
        "input_mode": "hybrid",
        "user_requirements": params.get("user_requirements", ""),
        "ai_role_profile": cst_settings.get(
            "ai_role_profile",
            "你是一个天线与电磁领域的专家，具有充足的电磁仿真经验以及CST软件的建模与仿真使经验，擅长超表面，天线罩，天线的设计与调参。",
        ),
        "goals": {
            "freq_range_GHz": [
                targets.get("freq_min_GHz", 2.4),
                targets.get("freq_max_GHz", 2.5),
            ],
            "s11_max_dB": targets.get("s11_max_dB", -10.0),
            "radiation": targets.get("radiation", {}),
        },
        "enabled_result_channels": result_channels,
        "allowed_result_channels": result_channels,
        "strict_result_required": bool(cst_settings.get("strict_result_required", True)),
        "port_plan": params.get("port_plan", {}),
        "initial_port_plan": params.get("initial_port_plan") or params.get("port_plan") or {},
        "enable_cst_error_ai_recovery": bool(cst_settings.get("enable_cst_error_ai_recovery", True)),
        "max_error_retries": int(cst_settings.get("max_error_retries", 3)),
        "adjustable_params": list(adjustable_params.keys()),
        "parameter_bounds": param_bounds,
        "structure_plan": structure_plan,
    }


def collect_result_snapshot(cst_ctrl, channels: List[str]) -> Dict[str, Any]:
    """按指定通道读取 CST 结果。"""
    snapshot: Dict[str, Any] = {}
    errors: List[str] = []

    if "s_params" in channels:
        if hasattr(cst_ctrl, "get_s_parameters_full"):
            s_data = cst_ctrl.get_s_parameters_full()
            if s_data.get("success"):
                snapshot["s_params"] = s_data
            else:
                errors.append(f"s_params: {s_data.get('message', 'unknown')}")
        else:
            s11 = cst_ctrl.get_s11_parameters()
            if s11.get("success"):
                snapshot["s_params"] = {
                    "success": True,
                    "channels": {
                        "S11": {
                            "frequencies_GHz": s11.get("frequencies_GHz", []),
                            "magnitude_dB": s11.get("s11_dB", []),
                            "phase_deg": [],
                        }
                    },
                    "summary": {
                        "s11_min_dB": s11.get("s11_min_dB"),
                        "freq_at_min_GHz": s11.get("freq_at_min_GHz"),
                        "bandwidth_10dB_MHz": s11.get("bandwidth_10dB_MHz"),
                    },
                }
            else:
                errors.append(f"s_params: {s11.get('message', 'unknown')}")

    if "radiation" in channels:
        if hasattr(cst_ctrl, "get_radiation_metrics"):
            rad = cst_ctrl.get_radiation_metrics()
            if rad.get("success"):
                snapshot["radiation"] = rad
            else:
                errors.append(f"radiation: {rad.get('message', 'unknown')}")
        else:
            errors.append("radiation: controller does not support radiation channel")

    return {
        "success": len(errors) == 0,
        "results": snapshot,
        "errors": errors,
    }


def evaluate_design(results: Dict[str, Any], design_task: Dict[str, Any]) -> Dict[str, Any]:
    """统一评估（仅 S 参数）。"""
    goals = design_task.get("goals", {})
    freq_min, freq_max = goals.get("freq_range_GHz", [2.4, 2.5])
    s11_threshold = goals.get("s11_max_dB", -10.0)

    eval_data = {
        "s_params_ok": True,
        "all_ok": True,
        "details": {},
    }

    s_summary = ((results.get("s_params") or {}).get("summary") or {})
    if s_summary:
        s11_min = s_summary.get("s11_min_dB", 999)
        freq_at_min = s_summary.get("freq_at_min_GHz", -1)
        eval_data["s_params_ok"] = (s11_min <= s11_threshold) and (freq_min <= freq_at_min <= freq_max)
        eval_data["details"]["s_params"] = {
            "s11_min_dB": s11_min,
            "freq_at_min_GHz": freq_at_min,
            "threshold_dB": s11_threshold,
            "target_freq_range": [freq_min, freq_max],
        }
    else:
        eval_data["s_params_ok"] = False
        eval_data["details"]["s_params"] = {"message": "missing"}

    eval_data["all_ok"] = eval_data["s_params_ok"]
    return eval_data


def _apply_error_fix(
    current_params: Dict[str, float],
    current_port_plan: Dict[str, Any],
    fix_plan: Dict[str, Any],
    design_task: Dict[str, Any],
) -> Tuple[Dict[str, float], Dict[str, Any], Dict[str, Any]]:
    """应用 AI 返回的修复方案，并做边界约束。返回 (new_params, new_port_plan, new_solver_plan)。"""
    new_params = dict(current_params)
    changes = fix_plan.get("parameter_changes", {})
    for k, v in changes.items():
        if k in new_params:
            v = float(v)
            bounds = (design_task.get("parameter_bounds", {}) or {}).get(k, {})
            if isinstance(bounds, dict):
                vmin, vmax = bounds.get("min"), bounds.get("max")
                if vmin is not None:
                    v = max(v, float(vmin))
                if vmax is not None:
                    v = min(v, float(vmax))
            new_params[k] = v
    new_port = fix_plan.get("port_plan") or current_port_plan
    solver_hint = fix_plan.get("solver_hint", "").strip()
    new_solver = {"solver_type": solver_hint} if solver_hint else {}
    return new_params, new_port if isinstance(new_port, dict) else {}, new_solver


def _handle_cst_error(
    cst_ctrl,
    ai_client,
    design_task: Dict[str, Any],
    params: Dict[str, float],
    port_plan: Dict[str, Any],
    history: List[Dict[str, Any]],
    error_msg: str,
    enable_recovery: bool,
    error_attempt: int,
    max_error_retries: int,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    处理 CST 错误：若启用 AI 接管且未超重试次数，则调用 AI 分析并返回修复方案；
    否则返回 None 表示应直接停止（由调用方构造停止结果）。
    Returns: fix_result dict with "fix_plan" and "retry" for retry; None 表示应停止（调用方需构造返回）
    """
    extra = extra or {}
    if error_attempt >= max_error_retries:
        return None
    if not enable_recovery or not hasattr(ai_client, "analyze_cst_error"):
        return None
    if not hasattr(cst_ctrl, "get_cst_error_report"):
        return None
    report = cst_ctrl.get_cst_error_report()
    try:
        fix = ai_client.analyze_cst_error(
            design_task=design_task,
            error_report=report,
            current_params=params,
            port_plan=port_plan,
            history=history,
        )
    except Exception as e:
        print(f"  [ErrorRecovery] AI 错误分析失败: {e}")
        return None
    if not fix.get("retry", False):
        print(f"  [ErrorRecovery] AI 建议停止: {fix.get('reasoning', '')}")
        return None
    print(f"  [ErrorRecovery] AI 建议重试: {fix.get('reasoning', '')}")
    return fix


def _has_actionable_cst_error(cst_ctrl) -> bool:
    """检查 CST 错误报告是否包含可用于 AI 修复的错误线索。"""
    if not hasattr(cst_ctrl, "get_cst_error_report"):
        return False
    report = cst_ctrl.get_cst_error_report() or {}
    if not isinstance(report, dict):
        return False

    message = str(report.get("message", "")).strip()
    if message:
        return True

    cst_report = report.get("cst_report") or {}
    if not isinstance(cst_report, dict):
        return False
    merged = "\n".join(str(v) for v in cst_report.values() if v)
    if not merged.strip():
        return False

    if re.search(r"\b(error|failed|fatal|exception)\b", merged, re.IGNORECASE):
        if re.search(r"\b0\s+errors?\b", merged, re.IGNORECASE):
            return False
        return True
    return False


def run_design_iteration(
    cst_ctrl,
    ai_client: DeepSeekClient,
    design_task: Dict[str, Any],
    current_params: Dict[str, float],
    history: List[Dict[str, Any]],
    project_path: str,
    current_port_plan: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], bool]:
    """
    运行一次设计迭代。若 CST 报错且启用 AI 接管，则收集错误报告交给 AI 分析并重试。
    """
    enable_recovery = bool(design_task.get("enable_cst_error_ai_recovery", True))
    max_error_retries = int(design_task.get("max_error_retries", 3))
    params = dict(current_params)
    port_plan = dict(current_port_plan or design_task.get("port_plan") or design_task.get("initial_port_plan") or {})
    solver_plan: Dict[str, Any] = {}

    for error_attempt in range(max_error_retries + 1):
        print(f"\n{'='*60}")
        print(f"迭代 #{len(history) + 1}" + (f" (错误修复尝试 {error_attempt + 1}/{max_error_retries + 1})" if error_attempt > 0 else ""))
        print(f"当前参数: {json.dumps(params, ensure_ascii=False)}")
        print(f"{'='*60}")

        if hasattr(cst_ctrl, "set_port_plan") and port_plan:
            cst_ctrl.set_port_plan(port_plan)
        if hasattr(cst_ctrl, "set_solver_plan"):
            cst_ctrl.set_solver_plan(solver_plan)

        # Step 1: 设置参数
        print("\n[1/4] 设置结构参数...")
        if not cst_ctrl.set_parameters(params):
            fix = _handle_cst_error(
                cst_ctrl, ai_client, design_task, params, port_plan, history,
                "设置参数失败", enable_recovery, error_attempt, max_error_retries,
            )
            if fix is None:
                return {"error": "设置参数失败"}, True
            params, port_plan, new_solver = _apply_error_fix(params, port_plan, fix.get("fix_plan", {}), design_task)
            if new_solver:
                solver_plan = new_solver
            boundary_hint = fix.get("fix_plan", {}).get("boundary_hint", "")
            if boundary_hint:
                print(f"  [ErrorRecovery] boundary_hint (供手动参考): {boundary_hint}")
            continue

        # Step 2: 运行仿真
        print("\n[2/4] 运行 CST 仿真...")
        if hasattr(cst_ctrl, "last_cst_error"):
            cst_ctrl.last_cst_error = {}
        if hasattr(cst_ctrl, "set_result_channels"):
            cst_ctrl.set_result_channels(design_task.get("enabled_result_channels", ["s_params"]))
        if not cst_ctrl.run_simulation(wait_complete=True):
            fix = _handle_cst_error(
                cst_ctrl, ai_client, design_task, params, port_plan, history,
                "仿真失败", enable_recovery, error_attempt, max_error_retries,
            )
            if fix is None:
                return {"error": "仿真失败"}, True
            params, port_plan, new_solver = _apply_error_fix(params, port_plan, fix.get("fix_plan", {}), design_task)
            if new_solver:
                solver_plan = new_solver
            boundary_hint = fix.get("fix_plan", {}).get("boundary_hint", "")
            if boundary_hint:
                print(f"  [ErrorRecovery] boundary_hint (供手动参考): {boundary_hint}")
            continue

        # Step 2.5: 即便仿真成功，也检查 CST 错误报告并按需触发 AI 修复
        if _has_actionable_cst_error(cst_ctrl):
            print("\n[2.5/4] 检测到 CST 错误报告，触发 AI 修复...")
            fix = _handle_cst_error(
                cst_ctrl, ai_client, design_task, params, port_plan, history,
                "仿真后检测到 CST 错误报告", enable_recovery, error_attempt, max_error_retries,
            )
            if fix is None:
                return {"error": "仿真后检测到 CST 错误报告"}, True
            params, port_plan, new_solver = _apply_error_fix(params, port_plan, fix.get("fix_plan", {}), design_task)
            if new_solver:
                solver_plan = new_solver
            boundary_hint = fix.get("fix_plan", {}).get("boundary_hint", "")
            if boundary_hint:
                print(f"  [ErrorRecovery] boundary_hint (供手动参考): {boundary_hint}")
            continue

        # Step 3: 读取结果通道
        print("\n[3/4] 读取仿真结果通道...")
        result_plan_channels = design_task.get("enabled_result_channels", ["s_params"])
        snapshot = collect_result_snapshot(cst_ctrl, result_plan_channels)

        strict_required = bool(design_task.get("strict_result_required", True))
        if strict_required and not snapshot.get("success", False):
            if hasattr(cst_ctrl, "last_cst_error"):
                cst_ctrl.last_cst_error = {"stage": "result_read", "message": "关键结果通道缺失", "details": {"errors": snapshot.get("errors", [])}}
            fix = _handle_cst_error(
                cst_ctrl, ai_client, design_task, params, port_plan, history,
                "关键结果通道缺失",
                enable_recovery, error_attempt, max_error_retries,
                extra={"missing": snapshot.get("errors", [])},
            )
            if fix is None:
                return {"error": "关键结果通道缺失", "missing": snapshot.get("errors", [])}, True
            params, port_plan, new_solver = _apply_error_fix(params, port_plan, fix.get("fix_plan", {}), design_task)
            if new_solver:
                solver_plan = new_solver
            boundary_hint = fix.get("fix_plan", {}).get("boundary_hint", "")
            if boundary_hint:
                print(f"  [ErrorRecovery] boundary_hint (供手动参考): {boundary_hint}")
            continue

        break  # 成功，跳出错误重试循环

    # Step 4: 评估结果
    evaluation = evaluate_design(snapshot.get("results", {}), design_task)

    # 记录本次迭代
    iteration_record = {
        "iteration": len(history) + 1,
        "params": params.copy(),
        "result_snapshot": snapshot,
        "evaluation": evaluation,
    }
    history.append(iteration_record)

    # Step 5: 检查是否满足要求
    if evaluation["all_ok"]:
        print("\n[OK] 设计已满足所有要求！")
        return {
            "success": True,
            "message": "设计完成",
            "final_params": params,
            "final_results": snapshot.get("results", {}),
            "evaluation": evaluation,
            "history": history,
        }, True

    # Step 6: 调用 AI 分析并获取新参数
    print(f"\n[4/4] 调用 AI 分析...")
    print(f"  当前未达标: S={evaluation.get('s_params_ok')}")

    try:
        ai_result = ai_client.analyze_design(
            design_task=design_task,
            current_params=params,
            current_results=snapshot.get("results", {}),
            history=history,
        )

        print(f"\n  AI 决策:")
        stop_decision = ai_result.get("stop_decision", {})
        print(f"    停止迭代: {stop_decision.get('stop', False)}")
        print(f"    原因: {stop_decision.get('reason', 'N/A')}")
        print(f"    建议参数: {json.dumps(ai_result.get('parameter_plan', {}).get('changes', {}), ensure_ascii=False)}")

        iteration_record["ai_decision"] = ai_result

        if stop_decision.get("stop", False):
            return {
                "success": True,
                "message": "AI 决定停止迭代",
                "final_params": params,
                "final_results": snapshot.get("results", {}),
                "evaluation": evaluation,
                "ai_decision": ai_result,
                "history": history,
            }, True

        return iteration_record, False

    except Exception as e:
        print(f"  AI 调用失败: {e}")
        return {
            "error": f"AI 调用失败: {e}",
            "history": history,
        }, True


def run_automatic_design(
    cst_ctrl,
    ai_client: DeepSeekClient,
    design_task: Dict[str, Any],
    initial_params: Dict[str, float],
    max_iterations: int = 10,
    project_path: str = "",
) -> Dict[str, Any]:
    """
    运行自动设计循环

    Args:
        cst_ctrl: CST 控制器实例
        ai_client: AI 客户端实例
        initial_params: 初始参数
        targets: 设计目标
        max_iterations: 最大迭代次数
        project_path: 项目文件路径

    Returns:
        完整的设计结果
    """
    print(f"\n{'#'*70}")
    print("#" + " "*68 + "#")
    print("#" + "  CST 自动设计系统".center(68) + "#")
    print("#" + " "*68 + "#")
    print(f"{'#'*70}")

    goals = design_task.get("goals", {})
    freq_min, freq_max = goals.get("freq_range_GHz", [2.4, 2.5])
    print(f"\n设计目标:")
    print(f"  频段: {freq_min:.2f} - {freq_max:.2f} GHz")
    print(f"  S11 <= {goals.get('s11_max_dB', -10.0):.1f} dB")
    print(f"\n初始参数: {json.dumps(initial_params, ensure_ascii=False)}")
    print(f"最大迭代次数: {max_iterations}")

    # 打开项目
    if project_path:
        print(f"\n打开项目: {project_path}")
        if not cst_ctrl.open_project(project_path):
            return {"error": "无法打开项目", "success": False}

    # 将目标频段传给控制器用于仿真前检查
    if hasattr(cst_ctrl, "set_design_targets"):
        try:
            cst_ctrl.set_design_targets({
                "freq_min_GHz": freq_min,
                "freq_max_GHz": freq_max,
            })
        except Exception:
            pass

    # 仿真前检查（求解器/边界/频率范围）
    if hasattr(cst_ctrl, "preflight_check"):
        try:
            check = cst_ctrl.preflight_check()
            if not check.get("success", False):
                return {
                    "error": "CST 设置检查失败",
                    "success": False,
                    "details": check,
                }
        except Exception as e:
            return {
                "error": f"CST 设置检查异常: {e}",
                "success": False,
            }

    # 设计循环
    current_params = initial_params.copy()
    current_port_plan: Dict[str, Any] = dict(
        design_task.get("port_plan") or design_task.get("initial_port_plan") or {}
    )
    current_structure_plan: Dict[str, Any] = dict(
        design_task.get("structure_plan") or {}
    )
    history: List[Dict[str, Any]] = []

    for iteration in range(max_iterations):
        # 每轮开始前应用 structure_plan（若存在）
        if current_structure_plan and current_structure_plan.get("structure_type"):
            if hasattr(cst_ctrl, "apply_structure_plan"):
                cst_ctrl.apply_structure_plan(current_structure_plan)
            for k, v in (current_structure_plan.get("params") or {}).items():
                if isinstance(v, (int, float)):
                    current_params[k] = float(v)
        result, should_stop = run_design_iteration(
            cst_ctrl=cst_ctrl,
            ai_client=ai_client,
            design_task=design_task,
            current_params=current_params,
            history=history,
            project_path=project_path,
            current_port_plan=current_port_plan if current_port_plan else None,
        )

        if should_stop:
            # 检查是否是最终成功结果
            if "final_params" in result:
                return result
            # 否则是错误，立即停止（避免“未读到结果还继续下一轮”导致死循环）
            print(f"\n[错误] 第 {iteration+1} 次迭代失败，已停止后续迭代。")
            return result

        # 获取新参数与端口计划继续下一轮
        ai_decision = result.get("ai_decision", {})
        new_params = ai_decision.get("parameter_plan", {}).get("changes", {})
        new_port_plan = ai_decision.get("port_plan", {})
        if new_port_plan:
            current_port_plan = new_port_plan
            new_channels = ai_decision.get("result_plan", {}).get("channels", [])
            if isinstance(new_channels, list) and new_channels:
                allowed = design_task.get("allowed_result_channels", new_channels)
                filtered = [c for c in new_channels if c in allowed]
                if filtered:
                    design_task["enabled_result_channels"] = filtered
        if new_params:
            # 允许 AI 添加新参数
            for key, value in new_params.items():
                if isinstance(value, (int, float)) and not key.startswith("_"):
                    v = float(value)
                    bounds = (design_task.get("parameter_bounds", {}) or {}).get(key, {})
                    if isinstance(bounds, dict):
                        vmin = bounds.get("min")
                        vmax = bounds.get("max")
                        if vmin is not None:
                            v = max(v, float(vmin))
                        if vmax is not None:
                            v = min(v, float(vmax))
                    current_params[key] = v

        # 更新 structure_plan 供下一轮使用
        structure_plan = ai_decision.get("structure_plan", {})
        if structure_plan and structure_plan.get("structure_type"):
            current_structure_plan.update(structure_plan)
            for k, v in (structure_plan.get("params") or {}).items():
                if isinstance(v, (int, float)):
                    current_params[k] = float(v)

    # 达到最大迭代次数
    print(f"\n[!] 已达到最大迭代次数 ({max_iterations})")
    return {
        "success": False,
        "message": f"达到最大迭代次数 {max_iterations}",
        "final_params": current_params,
        "history": history,
    }


def main():
    """主程序入口"""
    try:
        # 加载配置和参数
        config = load_config()
        params_path, params = load_params_from_cli()

        # 提取设计参数与任务协议
        design_params = {k: v for k, v in params.items() if k not in ["targets", "parameter_bounds"]}
        design_task = build_design_task(params, config)

        # 获取设置
        design_settings = config.get("design_settings", {})
        max_iterations = design_settings.get("max_iterations", 10)
        output_dir = Path(design_settings.get("output_dir", "outputs"))
        auto_save = design_settings.get("auto_save", True)

        # 确定项目路径
        project_path = params.get("project_path", "templates/antenna_template.cst")

        # 初始化控制器
        print("\n" + "="*70)
        print("初始化系统...")
        print("="*70)

        ai_client = init_ai_client(config)
        print("[OK] AI 客户端初始化成功")

        cst_ctrl = init_cst_controller(config)
        print("[OK] CST 控制器初始化成功")

        # 运行自动设计
        result = run_automatic_design(
            cst_ctrl=cst_ctrl,
            ai_client=ai_client,
            design_task=design_task,
            initial_params=design_params,
            max_iterations=max_iterations,
            project_path=project_path,
        )
        result["design_task"] = design_task

        # 保存最终项目
        if auto_save and result.get("success"):
            output_project = output_dir / "final_design.cst"
            cst_ctrl.save_project(str(output_project))
            result["output_project"] = str(output_project)

        # 释放资源
        cst_ctrl.close()

        # 保存结果
        output_dir.mkdir(parents=True, exist_ok=True)
        result_file = output_dir / "design_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # 额外保存每轮 AI 计划与结果快照，便于复盘
        history = result.get("history", [])
        if history:
            history_file = output_dir / "iteration_history.json"
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        # 打印最终结果
        print(f"\n{'='*70}")
        print("设计完成")
        print(f"{'='*70}")
        print(f"\n结果文件: {result_file.resolve()}")

        if result.get("success"):
            print(f"\n[OK] 设计成功!")
            print(f"最终参数: {json.dumps(result.get('final_params', {}), ensure_ascii=False)}")
            final_results = result.get("final_results", {})
            s_summary = (final_results.get("s_params", {}) or {}).get("summary", {})
            print(f"最终 S11: {s_summary.get('s11_min_dB', 'N/A')} dB @ {s_summary.get('freq_at_min_GHz', 'N/A')} GHz")
        else:
            print(f"\n[!] 设计未完全成功")
            print(f"原因: {result.get('message', result.get('error', '未知'))}")

        print(f"\n完整结果已保存到: {result_file.resolve()}")

        # 打印命令行结果
        print(f"\n" + "="*70)
        print("JSON 输出:")
        print("="*70)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        return 0 if result.get("success") else 1

    except Exception as e:
        print(f"\n[错误] 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
