# S-Parameter Optimizer

S11 目标优化迭代。

## 适用场景

- S11 优化
- 天线调参
- 反射系数调谐

## 可调用工具

- set_parameter
- run_solver
- read_s11

## 输入

- params: 当前参数
- targets: { freq_min_GHz, freq_max_GHz, s11_max_dB }

## 预留扩展

- phase_sweep: 相位扫描（待实现）
- structure_switcher: 结构切换（待实现）
