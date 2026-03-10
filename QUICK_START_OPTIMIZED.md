# CST 自动设计系统 - 优化版快速开始

## 🚀 优化后的工作流程（推荐）

### 核心改进：一键宏模式

**之前（4步操作）：**
1. 导入参数更新宏 → 2. 运行宏 → 3. 运行仿真 → 4. 导出 S11

**现在（1步操作）：**
1. **运行一键宏**（自动完成：参数更新 + 仿真 + S11导出）

---

## 快速开始（3 分钟上手）

### 步骤 1: 准备环境

```bash
# 安装依赖
pip install openai pywin32
```

### 步骤 2: 配置（可选）

编辑 `config.json`（使用自动宏模式）：
```json
{
  "deepseek_api_key": "your-api-key-here",  // 可选，不填则用模拟AI
  "cst_settings": {
    "controller_mode": "auto"  // 自动选择最佳模式
  }
}
```

### 步骤 3: 准备 CST 项目

1. 启动 **CST Studio Suite 2024**
2. 打开模板项目：`templates/antenna_template/`
3. **保持 CST 运行状态**

### 步骤 4: 运行自动设计

```bash
python cst_runner.py example_params.json
```

### 步骤 5: 一键执行（在 CST 中）

程序会提示：
```
================================================================================
AUTO-MACRO MODE: Single macro for all operations
================================================================================

1. In CST: Macros -> Import -> Select: outputs/cst_auto/auto_iteration_1.mcr
2. Run the macro - it will automatically:
   - Update parameters: {'patch_length': 12.0, 'patch_width': 10.0}
   - Rebuild the model
   - Run simulation
   - Export S11 to: outputs/cst_auto/s11_iteration_1.txt
3. After the macro completes, press Enter here
================================================================================
```

**在 CST 中操作：**
1. `Macros` → `Import` → 选择 `outputs/cst_auto/auto_iteration_1.mcr`
2. `Macros` → `Run` → **一键完成所有操作！**
3. 等待宏执行完成（会显示进度消息）
4. 在程序中按回车继续

### 步骤 6: 自动迭代

AI 分析结果后，会自动生成下一轮宏文件：
- `auto_iteration_2.mcr`
- `auto_iteration_3.mcr`
- ...

重复步骤 5，直到设计达标。

---

## 对比：操作步骤减少 75%

| 操作 | 标准文件模式 | 一键宏模式（新） |
|------|-------------|-----------------|
| 导入宏 | ✅ 1 次 | ✅ 1 次 |
| 运行参数更新 | ✅ 1 次 | ✅ 自动（在宏内） |
| 运行仿真 | ✅ 1 次 | ✅ 自动（在宏内） |
| 导出 S11 | ✅ 1 次 | ✅ 自动（在宏内） |
| **总计点击** | **4 次** | **1 次** |
| **每次迭代时间** | ~2-3 分钟 | ~1-2 分钟 |

---

## 控制器模式选择

根据你的环境选择最佳模式：

### 🥇 模式 1: Python API（全自动，无需手动）
**前提：** Python 3.10 或 3.11

```json
{
  "cst_settings": {
    "controller_mode": "python_api"
  }
}
```

**优点：**
- 完全自动化，无需任何手动操作
- 直接从内存读取 S11
- 最快最稳定

---

### 🥈 模式 2: 一键宏（推荐，当前可用）
**前提：** 任何 Python 版本

```json
{
  "cst_settings": {
    "controller_mode": "auto_macro"
  }
}
```

**优点：**
- 一次点击完成所有操作
- 自动等待仿真完成
- 自动导出 S11

**生成的宏示例：**
```vba
Sub Main()
    ' 1. 更新参数
    StoreDoubleParameter "patch_length", 12.0
    StoreDoubleParameter "patch_width", 10.0
    
    ' 2. 重建模型
    Rebuild
    
    ' 3. 运行仿真
    solver.Start
    Do While solver.IsSimulating
        Sleep 2000
    Loop
    
    ' 4. 导出 S11
    results.Item(i).ExportCurve "default", "...", True
    
    MsgBox "All done!"
End Sub
```

---

### 🥉 模式 3: 标准文件模式（分步操作）
**前提：** 任何 Python 版本

```json
{
  "cst_settings": {
    "controller_mode": "file"
  }
}
```

**适用场景：**
- 需要精细控制每步操作
- 调试和开发阶段

---

## 自动模式（推荐配置）

```json
{
  "cst_settings": {
    "controller_mode": "auto"
  }
}
```

程序会自动选择：
1. **Python 3.10/3.11** → Python API 模式（全自动）
2. **其他 Python 版本** → 一键宏模式（一键操作）
3. **所有情况失败** → 标准文件模式（分步操作）

---

## 故障排除

### 宏运行时出错？

**问题：** `solver.IsSimulating` 方法不存在

**解决：** 可能是 CST 版本不同。切换到标准文件模式：
```json
{
  "cst_settings": {
    "controller_mode": "file"
  }
}
```

### 找不到 S11 结果？

**确保：**
1. 模板项目中已定义 S-Parameters 仿真
2. 仿真成功完成（无错误）
3. 结果树中有 S11 数据

### 如何加快迭代速度？

**减少仿真时间：**
- 降低网格密度（Mesh）
- 减少频率扫描点
- 使用自适应网格（Adaptive Mesh）

---

## 高级技巧

### 批量生成宏

如果想一次性生成多轮宏，可以修改 `max_iterations`：
```json
{
  "design_settings": {
    "max_iterations": 5  // 生成 5 轮迭代宏
  }
}
```

程序会生成：
- `auto_iteration_1.mcr`
- `auto_iteration_2.mcr`
- ...
- `auto_iteration_5.mcr`

你可以在 CST 中依次运行，无需每次都回程序。

### 监控仿真进度

宏运行时会显示 Debug 消息：
```
Updating parameters...
Rebuilding model...
Starting simulation...
Waiting for simulation...
Simulating...
Simulation completed!
Exporting S11...
```

### 保存最终设计

在 `config.json` 中启用自动保存：
```json
{
  "design_settings": {
    "auto_save": true
  }
}
```

达标后会提示你在 CST 中保存最终项目。

---

## 下一步

1. **先用模拟模式测试 AI 逻辑：**
   ```bash
   # 编辑 config.json: "use_fake_controller": true
   python cst_runner.py example_params.json
   ```

2. **然后用一键宏模式连接真实 CST：**
   ```bash
   # 编辑 config.json: "use_fake_controller": false
   python cst_runner.py example_params.json
   ```

3. **考虑安装 Python 3.11 实现全自动：**
   - 下载：https://www.python.org/downloads/release/python-3119/
   - 安装后使用：`py -3.11 cst_runner.py example_params.json`

---

## 文件结构

```
outputs/cst_auto/
├── auto_iteration_1.mcr      # 第1轮：一键宏
├── auto_iteration_2.mcr      # 第2轮：一键宏（AI生成新参数后）
├── s11_iteration_1.txt         # 第1轮 S11 数据
├── s11_iteration_2.txt         # 第2轮 S11 数据
└── ...
```

每个宏文件都是独立的，你可以随时在 CST 中重新运行。
