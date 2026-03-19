# 右上子图：数值求解主链

```mermaid
flowchart LR
  classDef solve fill:#fff8f2,stroke:#c05621,stroke-width:2px,color:#7b341e;

  A0[reset_flow\n初始化 rho ux uy] --> A1[compute_macroscopic\n由 F 统计宏观量]
  A1 --> A2[equilibria\n计算平衡态 feq]
  A2 --> A3[BGK碰撞\nF += -(F-feq)/tau]
  A3 --> A4[bounce-back\n障碍物反弹]
  A4 --> A5[streaming\nnp.roll 沿离散方向迁移]
  A5 --> A6[边界条件\ninlet outlet top-bottom]
  A6 --> A7[step 完成]

  class A0,A1,A2,A3,A4,A5,A6,A7 solve
```
