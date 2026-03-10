# CST 自动设计系统 - 快速开始 (文件模式)

## 工作模式说明

系统支持三种 CST 控制模式：

### 1. 文件模式 (推荐) - `controller_mode: "file"`
- 生成 VBA 宏文件供 CST 导入
- 最稳定，不依赖 COM 接口
- 需要用户在 CST 中手动导入宏并运行

### 2. COM 模式 - `controller_mode: "com"`
- 直接通过 COM 接口控制 CST
- 可能因 CST 版本不同而失效
- 需要 CST 支持 COM 自动化

### 3. 模拟模式 - `controller_mode: "fake"` 或 `use_fake_controller: true`
- 不连接真实 CST，用于测试 AI 逻辑
- 快速验证程序流程

---

## 快速开始（文件模式）

### 步骤 1: 安装依赖

```bash
pip install openai pywin32
```

### 步骤 2: 配置 API Key（可选）

编辑 `config.json`：

```json
{
  "deepseek_api_key": "sk-your-api-key-here",  // 留空则使用模拟 AI
  "cst_settings": {
    "controller_mode": "file"  // 使用文件模式
  }
}
```

### 步骤 3: 准备 CST 项目

1. 启动 **CST Studio Suite 2024**
2. 打开模板项目：`templates/antenna_template/`
3. 确保项目中包含 S-Parameters 仿真设置
4. **保持 CST 运行状态**

### 步骤 4: 运行自动设计

```bash
python cst_runner.py example_params.json
```

### 步骤 5: 在 CST 中执行宏（按程序提示操作）

程序会提示：
```
============================================================
IMPORTANT: Manual action required in CST
============================================================
1. Go to CST: Macros -> Import -> Select: outputs/cst_work/update_params.mcr
2. Run the macro to update parameters
3. Run simulation manually
4. After simulation, export S11 or continue
============================================================
```

在 CST 中操作：
1. **导入宏**：`Macros` → `Import` → 选择 `outputs/cst_work/update_params.mcr`
2. **运行宏**：`Macros` → `Run` → 选择导入的宏 → 参数自动更新
3. **运行仿真**：点击 `Home` → `Start Simulation` (或按 F5)
4. **导出 S11**：程序会生成导出宏，按提示操作

### 步骤 6: 继续迭代

按程序提示按回车键继续，AI 会分析结果并给出新的参数建议。

---

## 工作流程示例

```
[程序] 生成参数宏 -> [用户] CST 中导入运行 -> [CST] 更新参数并仿真
                                            ↓
[用户] 导出 S11 数据 -> [程序] 读取分析 -> [AI] 决策优化
                                            ↓
         ←←←←←←←←← 不满足要求则继续迭代 ←←←←←←←←←
                                            ↓
                              满足要求 → 保存最终设计
```

---

## 文件说明

### 生成的文件

在 `outputs/cst_work/` 目录：

| 文件 | 用途 |
|------|------|
| `update_params.mcr` | 更新结构参数的 VBA 宏 |
| `export_s11.mcr` | 导出 S11 数据的 VBA 宏 |
| `cst_automation.py` | Python 自动化脚本（备用） |
| `s11_data.txt` | 导出的 S11 数据文件 |

### 输出结果

在 `outputs/` 目录：

| 文件 | 内容 |
|------|------|
| `design_result.json` | 完整设计记录和迭代历史 |
| `final_design.cst` | 最终 CST 项目文件（如果启用 auto_save） |

---

## 常见问题

### Q: COM 接口为什么不能用？
**A:** CST 2024 的 COM 接口可能需要特殊配置或管理员权限。文件模式更稳定可靠。

### Q: 能否完全自动化而不需要手动操作？
**A:** 目前 CST 的自动化接口有限。要实现完全自动化，可以考虑：
1. 使用 CST 的 Batch 模式运行宏
2. 使用 CST 内置的 Python 脚本（如果启用）
3. 联系 CST 支持获取自动化方案

### Q: 如何减少手动操作次数？
**A:** 可以修改参数文件增加 `max_iterations`，一次性生成多轮迭代的宏文件，但需要在 CST 中逐轮运行。

---

## 高级配置

### 修改配置文件

`config.json`：

```json
{
  "deepseek_api_key": "your-key",  // DeepSeek API Key
  "deepseek_model": "deepseek-chat",  // 模型选择

  "cst_settings": {
    "controller_mode": "file",  // file / com / fake
    "cst_exe_path": "D:/CST Studio Suite 2024/CST DESIGN ENVIRONMENT.exe",
    "simulation_timeout": 600
  },

  "design_settings": {
    "max_iterations": 10,  // 最大迭代次数
    "auto_save": true,     // 是否自动保存最终设计
    "output_dir": "outputs"
  }
}
```

### 修改设计参数

`example_params.json`：

```json
{
  "project_path": "templates/antenna_template",
  "patch_length": 12.0,    // 贴片长度 (mm)
  "patch_width": 10.0,   // 贴片宽度 (mm)
  "targets": {
    "freq_min_GHz": 2.4, // 目标频段下限
    "freq_max_GHz": 2.5, // 目标频段上限
    "s11_max_dB": -10.0  // S11 阈值
  }
}
```

---

## 测试模式

如果不想连接真实 CST，使用模拟模式：

```bash
# 编辑 config.json
{
  "cst_settings": {
    "use_fake_controller": true  // 启用模拟模式
  }
}

# 运行
python cst_runner.py example_params.json
```

这将模拟整个流程，不连接真实 CST，用于测试 AI 决策逻辑。
