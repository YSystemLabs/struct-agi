# Struct AGI

**结构主义人工智能**——探索一种以显式结构发现、保持与压缩为核心的学习范式。

## 核心主张

> 学习的核心问题，是如何从原始数据中抽取并保持那些对任务成立真正关键的结构。

当前主流方法依赖大规模参数拟合，能学会强大的相关性利用能力，但未必自发形成对结构的稳定把握。本项目试图走另一条路：让机器显式地发现结构、筛选结构、在抽象过程中保住结构。

## 研究阶段

### Phase 1：最小可证伪闭环（进行中）

在 ARC-AGI-2 与 ConceptARC 网格抽象任务上验证：

> 显式结构假设与保结构学习，是否能够比纯端到端黑箱拟合更稳定地支持少样本规则归纳、任务级泛化与概念诊断？

**五层架构**：感知 → 候选生成 → 结构筛选 → 求解 → 验证归因

**渐进增长**：知识状态 $K_t$ 随任务经验积累，按需扩展，通过三阶段改写（假设折叠 → 别名消除 → 死知识冻结）保持复杂度受控。

**当前进展**：Step 1 已作为最小闭环基线冻结；Step 2 已完成到“冻结边界 + 明确移交”的验收口径。当前稳定结果为：Step 2a 在 Copy1-6 与 Center1-6 上达到 8/12、按“有条件通过”接受；Step 2b 在新增四个概念组上达到 MoveToBoundary 3/6、ExtendToBoundary 2/6、ExtractObjects 2/6，并将 CleanUp 冻结为未收口能力缺口。当前工程状态已进入 Step 3A 准备阶段，即先处理 Step 2 显式移交的残差能力，再进入正式增长实验。

**理论与实验包说明**：Phase 1 的 Step 1/2 工程工作先形成了当前单任务基线；根目录下的 [可组合信息论](docs/draft/可组合信息论.md) 是对这些工程实践的后续理论综合。当前已整理成可复现实验包的是 [experiments/multi_preorder_minimal_validation](experiments/multi_preorder_minimal_validation/多预序对象发现最小验证实验.md)，但它目前只应视为理论启发下的探索性最小验证包，用于筛选多预序路线是否值得继续保留，而不应视为主理论的正式 Phase A 实验包。并行的自动对象发现探索还包括 [phase1/scripts/softWTA_softHebb_minimal_validation/SoftWTA 关系原型发现最小验证实验.md](phase1/scripts/softWTA_softHebb_minimal_validation/SoftWTA 关系原型发现最小验证实验.md)；[phase1/docs/structure-miner](phase1/docs/structure-miner/README.md) 仅保留旧实验路线的 brainstorming 补充，不作为正式理论或正式实验指导。

## 项目结构

```text
structuralist-agi/
├── README.md                     # 本文件
├── docs/
│   └── draft/
│       └── 可组合信息论.md        # 后续形成的理论纲领草案
├── experiments/
│   └── multi_preorder_minimal_validation/
│       ├── 多预序对象发现最小验证实验.md
│       ├── appendix_a_tasks.v0_9.json
│       ├── appendix_b_config.v0_9.json
│       └── validation_report.v0_9.json
├── 研究宣言-0v2.md                # 研究方向与基本立场
├── 公开数据集选择方案-0v1.md       # 数据集选型记录
├── 项目评估-claude.md             # 外部评估
└── phase1/                        # 第一阶段工作区
    ├── README.md                  # Phase 1 详细说明与脚本用法
    ├── docs/
    │   ├── 第一阶段研究计划-0v1.md  # 可执行研究计划
    │   ├── 第一阶段算法架构-0v4.md  # 算法架构设计（当前版本）
    │   ├── step1/                 # Step 1 设计、接口、实验与验收文档
    │   └── step2/                 # Step 2 设计、边界、实验与验收文档
    ├── datasets/raw/              # ARC-AGI-2, ConceptARC 原始数据
    ├── src/                       # Phase 1 / Step 1-2 实现代码
    ├── tests/                     # Step 1-2 单元测试
    ├── scripts/                   # 渲染、gallery 构建等工具脚本
    └── outputs/                   # SVG 预览、batch 报告、debug bundle 等可再生输出
```

## 关键文档

| 文档 | 说明 |
| --- | --- |
| [研究宣言](研究宣言-0v2.md) | 为什么需要结构主义路径，范畴论视角的动机 |
| [可组合信息论](docs/draft/可组合信息论.md) | 对既有工程实践的理论综合，以及后续 Phase A-D 的正式纲领 |
| [多预序对象发现最小验证实验](experiments/multi_preorder_minimal_validation/多预序对象发现最小验证实验.md) | 理论启发的探索性最小验证包，用于判断多预序路线是否值得继续保留 |
| [SoftWTA 关系原型发现最小验证实验](phase1/scripts/softWTA_softHebb_minimal_validation/SoftWTA 关系原型发现最小验证实验.md) | 并行探索中的另一条自动对象发现路线草案 |
| [Phase 1 研究计划](phase1/docs/第一阶段研究计划-0v1.md) | 研究边界、假设、方法框架、评测指标、成功标准 |
| [Phase 1 算法架构](phase1/docs/第一阶段算法架构-0v4.md) | 五层架构、DSL、MDL 筛选、渐进增长、知识改写 |
| [Step 1 实验与验收报告](phase1/docs/step1/Step1实验与验收报告-0v1.md) | Step 1 的实验设置、结果摘要、验收结论与阶段性判断 |
| [Step 2a 实验与验收报告](phase1/docs/step2/Step2a实验与验收报告-0v1.md) | Step 2a 的实验设置、冻结边界、全量回归与验收结论 |
| [Step 2b 实验与验收报告](phase1/docs/step2/Step2b实验与验收报告-0v1.md) | Step 2b 的实验设置、冻结边界、全量回归与验收结论 |
| [Phase 1 README](phase1/README.md) | 目录约定、脚本用法、本地预览方法 |

## 当前结论

截至 2026-04-06，项目最重要的阶段性结论是：Step 2 已经把单任务求解器推进到可冻结、可审计、可批量回归的稳定基线。当前 36 个训练任务的全量回归结果为 15/36 exact，且已知成功样例无回退；与此同时，Copy3-6、部分 ExtendToBoundary 残差与 CleanUp 缺口已经被明确登记为 Step 3A 输入，而不是继续回流 Step 2 做边界蔓延式修补。

## 数据集

- **ARC-AGI-2**：1000 训练 + 120 评估，二维离散彩色网格变换任务
- **ConceptARC**：16 个概念组 × 10 个任务，前 6 个作为结构先验训练集（训练排序模型），后 4 个作为机制诊断集（纯前向评测）

## License

研究项目，暂未设定开源许可证。
