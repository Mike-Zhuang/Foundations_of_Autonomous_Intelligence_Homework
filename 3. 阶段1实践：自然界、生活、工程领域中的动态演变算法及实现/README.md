<div align="center">

# 🌊 Lattice Boltzmann Method (LBM) Fluid Dynamics Simulation

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-Animation-orange.svg)](https://matplotlib.org/)
[![Numpy](https://img.shields.io/badge/Numpy-Optimized-success.svg)](https://numpy.org/)
[![LBM Model](https://img.shields.io/badge/Model-D2Q9-red.svg)]()

**自然界、生活、工程领域中的动态演变算法及实现** —— 一款拥有大厂级规范与高性能并发计算思路的二维计算流体力学（CFD）交互式实时仿真引擎。基于**格子玻尔兹曼方法（LBM D2Q9）**，支持卡门涡街、迷宫流体寻路求解及空气动力学升力仿真。

</div>

---

## 🌟 项目概述
本项目通过构建经典的 LBM D2Q9（二维九向）演化模型，模拟流体在复杂边界或障碍物下的动态行为（如卡门涡街产生的周期性旋涡剥离）。
程序高度工程化，在算法底层实现了基于 numpy 的全矩阵张量化计算，极大提升了模拟效率。同时，引擎拥有完整的前端交互 GUI（借助 matplotlib），你可以在流体运行时实时涂抹、擦除障碍物，导入迷宫图片测试流体通过性，并自动化进行广度优先（BFS）路径搜寻。

### 核心特性
- **⚡ 张量化 LBM 计算**：彻底摒弃低效的 `for` 循环，采用 Numpy Broadcasting 完成碰撞（Collision）与迁移（Streaming），在普通 CPU 上即能享受 800x200 网格的高斯平滑流体渲染。
- **🎮 即时交互与动态边界**：运行时支持鼠标左键拖拽“画擦”流体障碍。支持动态调参，实时观察雷诺数（Re）变化时的层流至湍流演变。
- **🧭 迷宫地图与 BFS 寻路与流场耦合**：支持图片格式的二值化地图导入，可将复杂图像转化为流体障碍。内置 BFS 最短路径求解并能够与流体流速热力图结合。
- **✈️ 航空工程扩展**：预置了 NACA 0012 翼型生成器，支持自定义攻角（Angle of Attack），适合模拟观察微观空力学现象。
- **🎥 视频/GIF 导出**：支持后台自动化渲染并导出具备透明叠加图层的 Mp4/GIF 动画，适合制作演示报告。

---

## 🛠️ 安装与运行

### 依赖环境
```bash
# 核心依赖
pip install numpy matplotlib

# 选装依赖（涉及读取外部图像作为障碍地图时需要）
pip install opencv-python
```

### 快速启动
在终端中进入该目录并运行主脚本：
```bash
python Simulation.py
```

### 命令行参数配置
支持通过命令行指令动态初始化仿真域参数：
```bash
python Simulation.py --ny 250 --nx 1000 --tau 0.58 --u-in 0.1 --steps-per-frame 8 --non-periodic-y
```
- `--ny`, `--nx`: 仿真晶格网格的长宽（决定分辨率）。
- `--tau`: 碰撞弛豫时间配置（影响流体粘性系数，$\nu = \frac{(\tau - 0.5)}{3}$）。
- `--u-in`: 入口流速。
- `--export`: 指定输出路径即可触发免交互渲染导出（如 `--export result.mp4 --export-frames 600`）。

---

## 🕹️ 交互操作指南 (测试方法)

程序启动后，会弹出 Matplotlib 可视化界面，分为左（速度幅值）右（涡量场/迷宫图）双面板。当光标在画布内时，你可使用以下快捷键进行实时控制：

| 快捷键 | 功能操作 |
| --- | --- |
| `Space (空格)`| **暂停 / 播放** 物理仿真 |
| `R` | **重置流场（Reset）**，将流场恢复为初始化状态 |
| `C` | **清空障碍物（Clear）**，一键清除场内所有墙壁与遮挡 |
| `D / E` | 切换鼠标画笔为 **画图 (Draw)** 或 **橡皮擦 (Erase)** 模式 |
| `鼠标左键拖拽` | 在画面中涂抹障碍物边界或擦除已有障碍 |
| `+ / -` | **增大或缩小** 鼠标画笔的半径（Brush Radius） |
| `↑ / ↓` | 微调（增加/减少）**碰撞弛豫时间 (tau)**，直观影响雷诺数 |
| `← / →` | 微调（减少/增加）**入口初始流速 (u_in)** |
| `1`~`4` | **切换物理预设** (1: 层流； 2: 中雷诺数； 3: 卡门涡街； 4: 高雷诺震荡) |
| `I` | **导入图像 (Image)** 读取并导入同目录下的 `obstacle.png` 作为流体迷宫 |
| `M` | 切屏：在 **涡量计算视图 (Vorticity)** 与 **流体迷宫 (Maze)** 视图之间切换 |
| `N` | 生成 **NACA 0012 翼型** (自带 8 度攻角，演示动态升力流场) |
| `S` | **快照 (Snapshot)**：保存当前帧流场为超清 PNG 截图 |

---

## 🧠 程序架构与核心思路

程序的底层引擎在 `LBMKarmanSimulation` 类中实现。

### 1. Lattice Boltzmann Method (LBM D2Q9)
代码采用了 D2Q9 (双维九离散速度) 架构定义流体微团：
- `CX` / `CY`: 刻画微团在 9 个离散方向上的速度分量。
- `W`: 各个方向的平衡态权重（中间 $4/9$，轴向 $1/9$，对角线 $1/36$）。
- `OPP`: 方向数组的反方向索引，用于实现基于“反弹边界法则 (Bounce-Back)”的固体边界。

**迭代步（Step）核心思路：**
1. **宏观量计算** (`compute_macroscopic`)：基于速度分布算子 $F$ 累加求出密度 $\rho$ 与宏观速度矩阵 $u_x, u_y$。
2. **碰撞过程 (Collision)**：执行单弛豫时间 (BGK) 模型近似：$F_i = F_i - \frac{1}{\tau} (F_i - F_i^{eq})$，由微观趋向平衡分布 $F_i^{eq}$。
3. **边界反弹 (Bounce-back)**：检测位于 `self.obstacle` 上的 $F_i$ 流体，强制反转其方向送回原位以满足诺一滑移（No-slip）边界。
4. **迁移/平流 (Streaming)**：基于 Numpy 的 `np.roll` 函数通过位移内存块实现 $F$ 粒子的极速网格移动。
5. **固定边界应用**：使用 Zou-He 速度边界作为左侧入水口常量输入，使用零梯度法配置右侧无阻碍出水口。

### 2. 气动翼型生成 (`set_naca0012_obstacle`)
并非单纯读图，算法依据 NACA4 位数公式实现了标准翼体厚度解析解。同时加入了坐标旋转变换支持自定义攻角（Angle of Attack），并通过 `MplPath` 和网格点光线投射碰撞测试将其解析成布尔掩码 `Boolean Mask`。

### 3. BFS 并行迷宫寻路算法 (`solve_maze_bfs`)
该算法不只演示流体力学，还包含一个由广度优先搜索驱动的路径发现逻辑：
1. 找出左端自由格子入列为 Seed。
2. 通过双端队列向右扩张试探 `(dy, dx)`，在流场中建立父节点历史（Parent Hash）。
3. 一旦接触右侧边界，立即回溯生成一条具有最少步数的最佳通路，并映射至前端呈现炫酷的绿色荧光。

---

> _"Simplicity is the ultimate sophistication."_ — 此项目的架构设计在保证学术精度的前提下，实现了极其优美的代码高内聚呈现，所有逻辑聚合于纯 Python 环境中，是对经典算法完美迁移工程的极佳范例。
