# Simulation.py 代码流程图说明

VS Code 默认的 Markdown 预览通常不能直接显示 Mermaid，所以我改成了更稳妥的方案：

- 直接使用横版 SVG 流程图：[Simulation_Code_Flowchart.svg](Simulation_Code_Flowchart.svg)

这张图更偏“流程图”而不是“脑图”，适合直接插入 PPT。

## 使用建议

1. 直接打开 [Simulation_Code_Flowchart.svg](Simulation_Code_Flowchart.svg)。
2. 如果 PPT 支持 SVG，优先直接插入，放大后依然清晰。
3. 如果你想截图，建议先全屏打开 SVG 再截，这样字更清楚。

## 讲解主线

答辩时建议按这个顺序讲：

1. 程序入口：`parse_args()` 和 `main()`。
2. 初始化：创建 `LBMKarmanSimulation`，设置网格、参数、障碍物。
3. 核心循环：`step()` 完成宏观量统计、碰撞、反弹、迁移、边界条件。
4. 物理量输出：速度、涡量、升力系数、雷诺数。
5. 可视化：左图速度，右图涡量，第三图升力历史。

如果你还想要一个“更简洁的一页版流程图”，我也可以继续帮你再压缩一版。
