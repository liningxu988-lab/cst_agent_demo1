# CST 自动设计系统

基于 DeepSeek AI 和 CST Studio Suite 的自动化天线设计工具。

## 功能特点

1. **自动建模**: 通过 CST COM 接口自动设置结构参数
2. **自动仿真**: 自动运行 CST 仿真并等待完成
3. **内存读取**: 直接从 CST 内存读取 S11 参数，无需导出文件
4. **AI 决策**: 调用 DeepSeek AI 分析结果并决定参数调整方向
5. **自动迭代**: 实现设计-仿真-优化-再设计的自动循环

## 项目结构

```
cst_agent_demo/
├── cst_runner.py          # 主程序入口
├── config.json            # 配置文件（填写 API Key）
├── example_params.json    # 参数示例文件
├── scripts/
│   ├── ai_client.py       # DeepSeek AI 客户端
│   ├── cst_controller.py  # CST COM 接口控制器
│   └── cst_bridge.py      # 原有桥接模块（保留）
├── templates/
│   └── antenna_template/  # CST 模板工程
└── outputs/               # 输出目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install openai pywin32
```

### 2. 配置 API Key

编辑 `config.json`，填入你的 DeepSeek API Key：

```json
{
  "deepseek_api_key": "sk-xxxxxxxxx",
  "deepseek_model": "deepseek-chat",
  "deepseek_base_url": "https://api.deepseek.com"
}
```

### 3. 运行自动设计

```bash
# 使用示例参数运行
python cst_runner.py example_params.json
```

### 4. Kiko 交互式助手（反射单元建模）

```bash
python kiko.py
```

启动后进入 Kiko 模式，用自然语言描述需求，例如：
- 「我想设计 2.45GHz 的反射单元，贴片 12x10mm」
- 「中心频率 3GHz，请仿真并给出 S11」
- 「优化」或「继续」启动 AI 自动调参

Kiko 固定建模条件：Background、FloquetPort 边界、x/y unit cell、z open、zmax=λ/2。

## 参数文件格式

```json
{
  "project_path": "templates/antenna_template.cst",
  "patch_length": 12.0,
  "patch_width": 10.0,
  "targets": {
    "freq_min_GHz": 2.4,
    "freq_max_GHz": 2.5,
    "s11_max_dB": -10.0
  }
}
```

- `project_path`: CST 模板工程路径
- `patch_length`, `patch_width`: 结构参数（可根据模板修改）
- `targets`: 设计目标
  - `freq_min_GHz`, `freq_max_GHz`: 目标频段
  - `s11_max_dB`: S11 阈值（如 -10dB）

## 配置文件说明

`config.json`:

```json
{
  "deepseek_api_key": "your-api-key-here",
  "deepseek_model": "deepseek-chat",
  "deepseek_base_url": "https://api.deepseek.com",
  
  "cst_settings": {
    "auto_find_cst": true,      // 自动查找 CST 安装
    "cst_exe_path": "",          // 手动指定 CST 路径
    "use_fake_controller": false, // 使用模拟控制器（测试）
    "simulation_timeout": 600     // 仿真超时时间（秒）
  },
  
  "design_settings": {
    "max_iterations": 10,        // 最大迭代次数
    "auto_save": true,           // 自动保存最终设计
    "output_dir": "outputs"      // 输出目录
  }
}
```

## 工作模式

### 模式 A: 真实 CST 模式（默认）

连接真实运行的 CST Studio Suite，通过 COM 接口：
- 设置参数
- 运行仿真
- 从内存读取 S11

### 模式 B: 模拟测试模式

设置 `use_fake_controller: true`，使用 FakeCSTController：
- 不连接真实 CST
- 基于参数计算模拟的 S11 结果
- 用于测试 AI 决策逻辑

## 设计流程

```
开始
  │
  ▼
加载配置和参数
  │
  ▼
初始化 AI 客户端 & CST 控制器
  │
  ▼
打开 CST 项目
  │
  ├─────────────────────────────┐
  │                             │
  ▼                             │
设置结构参数 ──→ 运行仿真 ──→ 读取 S11 ──→ AI 分析 ──→ 满足要求?
                                                 │          │
                                                 │    是 ───┘
                                                 │          │
                                                 │    否 ───→ 更新参数 ─┐
                                                 │                     │
                                                 └─────────────────────┘
```

## 输出结果

设计完成后，会在 `outputs/` 目录生成：

1. `design_result.json`: 完整设计记录，包括：
   - 每次迭代的参数
   - S11 仿真结果
   - AI 决策记录
   - 最终设计参数

2. `final_design.cst`: 最终保存的 CST 工程文件（可编辑）

## 扩展开发

### 添加新的结构参数

在参数文件中直接添加：

```json
{
  "patch_length": 12.0,
  "patch_width": 10.0,
  "substrate_height": 1.6,
  "feed_position": 3.0
}
```

确保 CST 模板工程中已定义同名参数。

### 添加更多 S 参数

编辑 `scripts/cst_controller.py` 中的 `get_s11_parameters()` 方法，
可以扩展读取 S21、S12 等其他参数。

## 注意事项

1. **CST 版本**: 支持 CST Studio Suite 2022 及以上版本
2. **Windows 系统**: 需要 Windows 系统（使用 COM 接口）
3. **权限**: 确保 CST 已激活，可以正常运行仿真
4. **网络**: 调用 DeepSeek API 需要网络连接

## 故障排除

### 问题: 无法连接到 CST

解决: 
- 确保 CST 已安装并激活
- 检查 `cst_settings.cst_exe_path` 是否正确
- 尝试先手动启动 CST，再运行脚本

### 问题: AI 调用失败

解决:
- 检查 `config.json` 中的 API Key 是否正确
- 确认网络可以访问 https://api.deepseek.com
- 查看是否超出 API 调用配额

### 问题: 无法读取 S11 参数

解决:
- 确保仿真已成功完成
- 检查模板工程中是否有 S 参数仿真设置
- 尝试使用 `use_fake_controller: true` 测试模式排查

## License

MIT License
