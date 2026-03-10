# CST 全自动设计方案 - 无需人工介入

## 方案对比

| 方案 | 自动化程度 | 配置 | 前提条件 |
|------|-----------|------|---------|
| **Python API** | 🟢 100% 自动 | `controller_mode: "python_api"` | Python 3.10 或 3.11 |
| **批处理模式** | 🟢 95% 自动 | `controller_mode: "batch"` | CST 2024 |
| **一键宏** | 🟡 一键/轮 | `controller_mode: "auto_macro"` | 任意 Python |
| **文件模式** | 🔴 手动 | `controller_mode: "file"` | 任意 Python |

---

## 方案 1: Python API 模式（推荐 - 完全自动）

### 前提
- Python 3.10 或 3.11

### 安装 Python 3.11
```bash
# 下载并安装 Python 3.11
https://www.python.org/downloads/release/python-3119/

# 验证安装
py -3.11 --version
```

### 配置
```json
{
  "cst_settings": {
    "controller_mode": "python_api"
  }
}
```

### 运行
```bash
py -3.11 -m pip install openai pywin32
py -3.11 cst_runner.py example_params.json
```

**结果:** 完全自动，无需任何人工操作

---

## 方案 2: 批处理模式（当前推荐）

### 配置
```json
{
  "cst_settings": {
    "controller_mode": "batch"
  }
}
```

### 工作原理
1. 程序自动生成 VBA 宏（包含参数更新+仿真+导出）
2. 生成 Windows 批处理脚本 (.bat)
3. 脚本自动启动 CST 并执行宏
4. 监控完成标志文件
5. 自动读取 S11 结果

### 运行
```bash
python cst_runner.py example_params.json
```

**结果:** 
- 只需启动程序，后续全自动
- CST 会自动启动、执行、导出
- 程序自动检测完成并继续迭代

---

## 方案 3: 当前系统（Python 3.14）的批处理模式配置

### 步骤 1: 配置 config.json
```json
{
  "deepseek_api_key": "your-api-key-here",
  "cst_settings": {
    "controller_mode": "batch",
    "auto_find_cst": true,
    "simulation_timeout": 600
  },
  "design_settings": {
    "max_iterations": 10,
    "auto_save": true,
    "output_dir": "outputs"
  }
}
```

### 步骤 2: 准备 CST 项目
确保 `templates/antenna_template/` 包含完整的 CST 项目结构。

### 步骤 3: 运行全自动设计
```bash
python cst_runner.py example_params.json
```

程序会自动：
1. ✅ 检测 Python 版本（3.14，跳过 Python API）
2. ✅ 选择批处理模式
3. ✅ 生成自动执行宏
4. ✅ 启动 CST 并运行
5. ✅ 等待仿真完成
6. ✅ 读取 S11 结果
7. ✅ AI 分析并生成新参数
8. ✅ 下一轮迭代...

---

## 全自动工作流程

```
[开始]
   |
   v
[程序] 生成参数+宏+批处理脚本
   |
   v
[批处理] 启动 CST → 导入宏 → 自动执行
   |                       |
   |                       v
   |              [CST内部] 参数更新
   |                       重建模型
   |                       运行仿真
   |                       导出 S11
   |                       写完成标志
   |                       |
   v                       v
[程序] 检测完成标志 ←——— 完成
   |
   v
[程序] 读取 S11 文件
   |
   v
[AI] 分析结果
   |
   +-- 未达标 --→ 生成新参数 --→ [下一轮]
   |
   +-- 已达标 --→ 保存结果 --→ [结束]
```

---

## 生成的文件结构

```
outputs/cst_batch/
├── auto_run_1.mcr          # 第1轮 VBA 宏
├── run_iteration_1.bat      # 第1轮 批处理
├── s11_iter_1.txt          # 第1轮 S11 结果
├── s11_iter_1.txt.done     # 第1轮 完成标志
├── auto_run_2.mcr          # 第2轮 VBA 宏
├── run_iteration_2.bat      
├── s11_iter_2.txt
├── s11_iter_2.txt.done
└── ...
```

---

## 故障排除

### CST 无法自动启动？

**检查:**
```bash
# 确认 CST 路径
ls "D:\Program Files (x86)\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe"

# 手动测试批处理
cd outputs/cst_batch
run_iteration_1.bat
```

### 宏执行失败？

**可能原因:**
1. 项目未正确保存
2. 宏安全性设置阻止自动执行

**解决:**
在 CST 中：
- `File` → `Options` → `Macro` → 设置信任级别

### S11 无法导出？

**检查项目模板:**
1. 确认有 S-Parameters 仿真设置
2. 确认仿真频率范围覆盖目标频段
3. 检查 S11 结果名称（可能是 "S1,1" 或 "S11"）

---

## 性能优化

### 加快仿真速度

在 CST 模板中调整：
1. **网格密度**: 降低 Mesh 密度
2. **频率点数**: 减少扫频点数
3. **自适应网格**: 启用 Adaptive Mesh

### 减少迭代次数

在 `example_params.json` 中提供更好初值：
```json
{
  "patch_length": 11.5,  // 接近最优值
  "patch_width": 10.0,
  "targets": {
    "freq_min_GHz": 2.4,
    "freq_max_GHz": 2.5,
    "s11_max_dB": -10.0
  }
}
```

---

## 完整示例

### 运行命令
```powershell
cd e:\code\cst_agent_demo
python cst_runner.py example_params.json
```

### 预期输出
```
======================================================================
Initializing system...
======================================================================
[Note] No DeepSeek API Key configured, using simulated AI client
[OK] AI client initialized successfully
[Batch] CST found: D:\Program Files (x86)\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe
[Mode] Using CSTBatchController (Batch/Auto-run mode)
       FULLY AUTOMATIC - Generates batch scripts
       Auto-starts CST and executes macros
[OK] CST controller initialized successfully

######################################################################
#                                                                    #
#                    CST Auto Design System                          #
#                                                                    #
######################################################################

Design Targets:
  Band: 2.40 - 2.50 GHz
  S11 <= -10.0 dB

Initial params: {"patch_length": 12.0, "patch_width": 10.0}
Max iterations: 10

Project: templates/antenna_template
[Batch] Generated files:
  Macro: outputs\cst_batch\auto_run_1.mcr
  Batch: outputs\cst_batch\run_iteration_1.bat
  Export: outputs\cst_batch\s11_iter_1.txt

[Batch] Starting automated execution...
[Batch] CST process started (PID: 12345)

[Batch] Waiting for CST to complete (timeout: 600s)...
  [Batch] Waiting...
  [Batch] Waiting...
[Batch] Completion detected!

S11 Results:
  S11 min: -8.5 dB @ 2.35 GHz
  10dB BW: 0.0 MHz

[4/4] AI Analysis...
  Current: S11=False, Freq=False
  
  AI Decision:
    Stop iteration: False
    Reason: S11=-8.5dB not meeting target
    New params: {"patch_width": 10.5}

====================================================================
Iteration #2
====================================================================
...
```

---

## 下一步

现在可以运行测试：

```bash
# 使用批处理全自动模式
python cst_runner.py example_params.json
```

系统会自动：
1. 选择批处理模式（因为 Python 3.14 不兼容 Python API）
2. 生成自动执行脚本
3. 启动 CST
4. 全自动迭代直到达标或达到最大次数

准备好测试了吗？
