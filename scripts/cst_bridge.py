import json
import subprocess
from pathlib import Path


def find_cst_installation() -> dict:
    install_base = Path(r"D:\Program Files (x86)\CST Studio Suite 2024")

    cst_exe_candidates = [
        Path(r"D:\Program Files (x86)\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe"),
    ]

    found_exes = [str(p) for p in cst_exe_candidates if p.exists()]

    return {
        "install_base": str(install_base),
        "install_exists": install_base.exists(),
        "exe_candidates_checked": [str(p) for p in cst_exe_candidates],
        "found_exes": found_exes,
        "cst_found": install_base.exists(),
        "exe_found": len(found_exes) > 0,
    }


def try_launch_cst(cst_exe: str, project_path: str) -> dict:
    try:
        proc = subprocess.Popen([cst_exe, project_path])
        return {
            "launch_success": True,
            "pid": proc.pid,
            "opened_project": project_path,
            "message": "已尝试启动 CST 并打开模板工程"
        }
    except Exception as e:
        return {
            "launch_success": False,
            "error": str(e),
            "message": "启动 CST 并打开模板工程失败"
        }


def extract_model_params(params: dict) -> dict:
    model_params = {}
    for key, value in params.items():
        if key != "targets":
            model_params[key] = value
    return model_params


def write_param_task(project_path: str, output_dir: str, model_params: dict) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    task = {
        "project_path": project_path,
        "model_params": model_params
    }

    task_file = output_path / "cst_param_task.json"
    task_file.write_text(
        json.dumps(task, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return str(task_file.resolve())


def write_cst_param_update_script(output_dir: str, model_params: dict) -> str:
    """
    生成一个待接入 CST API 的参数更新脚本模板。
    先不保证可直接运行，目标是把“参数更新意图”固化下来。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    lines = [
        "# 这是自动生成的 CST 参数更新脚本模板",
        "# 下一步你需要根据 CST 当前版本的 Python API，把下面的占位逻辑替换成真实调用",
        "",
        f"model_params = {repr(model_params)}",
        "",
        "print('准备更新以下参数:')",
        "for k, v in model_params.items():",
        "    print(f'  {k} = {v}')",
        "",
        "# TODO: 在这里接入真实 CST API",
        "# 例如：",
        "# project = ...",
        "# for k, v in model_params.items():",
        "#     project.set_parameter(k, v)",
        "# project.save()",
        "",
        "print('参数更新脚本模板已执行（当前仍是占位版）')",
    ]

    script_file = output_path / "cst_param_update.py"
    script_file.write_text("\n".join(lines), encoding="utf-8")
    return str(script_file.resolve())


def run_cst_simulation(project_path: str, output_dir: str, params: dict) -> dict:
    project = Path(project_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    project_exists = project.exists()
    project_suffix_ok = project.suffix.lower() == ".cst"

    cst_probe = find_cst_installation()

    launch_info = {
        "launch_success": False,
        "message": "未找到可执行文件，未尝试启动"
    }

    if cst_probe["exe_found"]:
        cst_exe = cst_probe["found_exes"][0]
        launch_info = try_launch_cst(cst_exe, str(project.resolve()))

    model_params = extract_model_params(params)

    param_task_file = write_param_task(
        project_path=str(project.resolve()) if project_exists else str(project),
        output_dir=str(output_path),
        model_params=model_params
    )

    param_update_script = write_cst_param_update_script(
        output_dir=str(output_path),
        model_params=model_params
    )

    bridge_result = {
        "success": project_exists and project_suffix_ok,
        "project_path": str(project.resolve()) if project_exists else str(project),
        "project_exists": project_exists,
        "project_suffix_ok": project_suffix_ok,
        "output_dir": str(output_path.resolve()),
        "received_params": params,
        "model_params": model_params,
        "param_task_file": param_task_file,
        "param_update_script": param_update_script,
        "cst_probe": cst_probe,
        "launch_info": launch_info,
        "message": "已完成模板工程、主程序探测、启动测试，并生成参数任务与参数更新脚本模板"
    }

    debug_file = output_path / "bridge_debug.json"
    debug_file.write_text(
        json.dumps(bridge_result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return bridge_result