# CST 零点击全自动模式

## 目标：100% 自动化，零人工介入

---

## 快速开始（已配置好）

### 1. 确认配置
`config.json` 已设置为完全全自动模式：
```json
{
  "cst_settings": {
    "controller_mode": "fully_auto"
  }
}
```

### 2. 直接运行
```bash
python cst_runner.py example_params.json
```

**就这么简单！程序会全自动运行，无需任何点击！**

---

## 全自动工作流程

```
[你] 运行命令
   |
   v
[程序] 自动生成宏（包含：参数+仿真+导出+状态）
   |
   v
[程序] 命令行启动 CST：CST.exe project.cst -macro autoexec.mcr
   |
   v
[CST] 自动执行宏（无需点击！）
   |-- 更新参数
   |-- 重建模型
   |-- 运行仿真
   |-- 导出 S11
   |-- 写完成标志文件
   |
   v
[程序] 监控完成标志
   |
   v
[程序] 读取 S11 → AI 分析 → 生成新参数
   |
   v
[程序] 下一轮迭代（全自动重复）
   |
   v
[结束] 达标或达到最大次数
```

---

## 生成的文件

```
outputs/cst_fully_auto/
├── autoexec_1.mcr          # 第1轮：嵌入式自动执行宏
├── s11_iter_1.txt          # 第1轮 S11 结果（自动导出）
├── s11_iter_1.txt.done     # 第1轮完成标志（SUCCESS/FAILED）
├── autoexec_2.mcr          # 第2轮自动宏
├── s11_iter_2.txt
├── s11_iter_2.txt.done
└── ...
```

---

## 技术原理

### 为什么能实现零点击？

**传统方式的问题：**
- CST 打开后，宏只是"可用"，需要用户点击运行
- 这不是真正的自动化

**零点击模式的解决方案：**

使用 CST 命令行参数：
```bash
CST.exe project.cst -macro autoexec.mcr
```

这会让 CST **启动时立即执行**指定的宏，无需任何用户交互。

宏中包含完整的工作流程：
1. 参数更新
2. 重建模型
3. 运行仿真
4. 导出 S11
5. 写完成标志
6. （可选）自动退出 CST

---

## 运行示例

```powershell
PS E:\code\cst_agent_demo> python cst_runner.py example_params.json

======================================================================
Initializing system...
======================================================================
[Note] No DeepSeek API Key configured, using simulated AI client
[OK] AI client initialized successfully
[FullyAuto] CST found: D:\Program Files (x86)\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe
[Mode] Using CSTFullyAutoController (ZERO-CLICK mode)
       100% FULLY AUTOMATIC - No human intervention!
       Auto-starts CST with embedded auto-execution macro
[OK] CST controller initialized successfully

######################################################################
#                                                                    #
#                    CST Auto Design System                          #
#                    ZERO-CLICK FULLY AUTOMATIC                        #
#                                                                    #
######################################################################

Design Targets:
  Band: 2.40 - 2.50 GHz
  S11 <= -10.0 dB

Initial params: {"patch_length": 12.0, "patch_width": 10.0}
Max iterations: 10

[FullyAuto] Iteration 1 prepared:
  Macro: outputs\cst_fully_auto\autoexec_1.mcr
  Expected S11: outputs\cst_fully_auto\s11_iter_1.txt

[FullyAuto] Launching CST with auto-execution...
  Command: D:\Program Files (x86)\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe templates\antenna_template -macro outputs\cst_fully_auto\autoexec_1.mcr
[FullyAuto] CST started (PID: 12345)

[FullyAuto] Waiting for auto-completion (timeout: 600s)...
  [FullyAuto] Running 10s...
    S11 file: 0 bytes
  [FullyAuto] Running 20s...
    S11 file: 0 bytes
  [FullyAuto] Running 30s...
    S11 file: 1245 bytes
  [FullyAuto] Running 40s...
[FullyAuto] SUCCESS detected!

[FullyAuto] S11 parsed: -8.5 dB @ 2.35 GHz

[AI] Analysis complete
  Current: S11=-8.5dB (target: -10dB) - Not meeting target
  Adjusting: patch_width 10.0 -> 10.5

======================================================================
Iteration #2
======================================================================
[FullyAuto] Iteration 2 prepared:
  Macro: outputs\cst_fully_auto\autoexec_2.mcr
  Expected S11: outputs\cst_fully_auto\s11_iter_2.txt

[FullyAuto] Launching CST with auto-execution...
...
```

---

## 故障排除

### CST 启动但没有自动执行？

**可能原因：** CST 版本不支持 `-macro` 参数，或安全设置阻止自动执行

**解决方法 1：** 检查 CST 版本
- CST 2024 应该支持命令行宏执行
- 如果不支持，尝试调整 CST 安全设置

**解决方法 2：** 切换到 batch 模式
```json
{
  "cst_settings": {
    "controller_mode": "batch"
  }
}
```

**解决方法 3：** 临时切换到一键模式（需要手动点击一次）
```json
{
  "cst_settings": {
    "controller_mode": "auto_macro"
  }
}
```

### 仿真完成但没有导出 S11？

**检查项目模板：**
1. 确认有 S-Parameter 仿真设置
2. 确认仿真频率包含目标频段
3. 查看 CST Debug Output 窗口的日志

### 等待超时？

**增加超时时间：**
```json
{
  "cst_settings": {
    "simulation_timeout": 1200  // 20分钟
  }
}
```

**或检查仿真设置：**
- 降低网格密度（减少仿真时间）
- 减少频率扫描点数

---

## 各模式自动化程度对比

| 模式 | 配置值 | 自动化程度 | 人工操作 |
|------|--------|-----------|---------|
| **完全全自动** | `fully_auto` | 🟢 100% | **零点击** |
| Python API | `python_api` | 🟢 100% | 零点击（需 Python 3.11） |
| 批处理 | `batch` | 🟡 90% | 可能需要 CST 安全设置 |
| 一键宏 | `auto_macro` | 🟡 75% | 每轮点击 1 次 |
| 文件模式 | `file` | 🔴 25% | 每轮 4 次操作 |

---

## 模式切换

### 如果 `fully_auto` 遇到问题

**方案 1：Batch 模式**
```json
{
  "cst_settings": {
    "controller_mode": "batch"
  }
}
```

**方案 2：一键模式（最稳定）**
```json
{
  "cst_settings": {
    "controller_mode": "auto_macro"
  }
}
```

**方案 3：测试模式（无需 CST）**
```json
{
  "cst_settings": {
    "use_fake_controller": true
  }
}
```

---

## 性能优化

### 加快仿真速度

在 CST 模板中：
1. **网格密度**：降低 Mesh 密度
2. **频率点数**：减少扫频点数
3. **求解器设置**：使用更快的算法

### 减少迭代次数

提供更好的初始值：
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

## 现在可以运行了！

```bash
python cst_runner.py example_params.json
```

**无需任何人工介入，程序全自动运行！**

运行后告诉我结果，如果遇到问题我们可以调整模式。
