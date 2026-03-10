# CST 自动设计系统 - 快速开始

## 使用步骤

### 1. 准备环境

**安装依赖:**
```bash
pip install openai pywin32
```

**配置 API Key (可选，不配置则使用模拟AI):**
编辑 `config.json`，填入你的 DeepSeek API Key：
```json
{
  "deepseek_api_key": "sk-your-api-key-here"
}
```

### 2. 启动 CST Studio Suite 2024

**请先手动启动 CST:**
1. 打开 CST Studio Suite 2024
2. 打开或创建你的天线模板项目
3. 确保项目中有 S-Parameters 仿真设置
4. 保持 CST 运行状态

**模板项目路径:** `templates/antenna_template/`

模板中应包含：
- 参数化结构（patch_length, patch_width）
- S-Parameters 仿真任务

### 3. 运行自动设计

```bash
python cst_runner.py example_params.json
```

程序将：
1. 连接运行中的 CST 实例
2. 根据参数修改模型
3. 运行仿真
4. 从内存读取 S11 结果
5. AI 分析并决定是否需要调整参数
6. 自动迭代直到满足目标
7. 保存最终设计

## 运行模式

### 模式1: 模拟模式（测试用，无需真实 CST）

编辑 `config.json`:
```json
{
  "cst_settings": {
    "use_fake_controller": true
  }
}
```

### 模式2: 真实 CST 模式

编辑 `config.json`:
```json
{
  "cst_settings": {
    "use_fake_controller": false,
    "auto_find_cst": true
  }
}
```

## 参数说明

**example_params.json:**
```json
{
  "project_path": "templates/antenna_template",  // CST 项目路径
  "patch_length": 12.0,                          // 结构参数（mm）
  "patch_width": 10.0,                           // 结构参数（mm）
  "targets": {
    "freq_min_GHz": 2.4,                        // 目标频段下限
    "freq_max_GHz": 2.5,                        // 目标频段上限
    "s11_max_dB": -10.0                         // S11 阈值
  }
}
```

## 常见问题

### Q: 无法连接到 CST
**A:** 请先手动启动 CST Studio Suite 2024，保持运行状态，然后再运行程序。

### Q: 读取 S11 失败
**A:** 确保模板项目中已运行过 S-Parameters 仿真，有 S11 结果数据。

### Q: AI 调用失败
**A:** 如果不配置 API Key，程序会自动使用模拟 AI。要启用真实 AI，需在 config.json 中配置 deepseek_api_key。

## 输出文件

运行完成后，在 `outputs/` 目录生成：
- `design_result.json` - 完整设计记录
- `final_design.cst` - 最终 CST 项目（如启用 auto_save）
