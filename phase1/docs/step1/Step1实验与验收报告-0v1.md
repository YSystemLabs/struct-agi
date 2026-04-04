# 第一阶段 Step 1 实验与验收报告

> 版本：v0.1
>
> 状态：已验收
>
> 日期：2026-04-04
>
> 作用：汇总 Step 1 的实验设置、关键结果、接口收口情况与最终验收结论。

## 1. 实验目标与范围

Step 1 的目标不是做通用 ARC 求解器，而是在严格受限边界内，完成一个可审计的最小闭环：从 train pairs 中产生候选结构，组装 hypothesis，执行程序，并输出最小归因。

本阶段实验只覆盖 ConceptARC 的 Copy1-6 与 Center1-6 共 12 个训练任务；Copy7-10 与 Center7-10 继续作为 Step 1-2 不可见诊断集。Step 1 明确不追求完整原语覆盖、不引入排序模型或知识写回，也不以 12/12 精确求解为验收前提。

## 2. 实验设置

本次实验使用 [Step1实现设计-0v1.md](phase1/docs/step1/Step1实现设计-0v1.md)、[Step1最小接口与任务清单附录-0v1.md](phase1/docs/step1/Step1最小接口与任务清单附录-0v1.md) 和 [Step1实现任务分解清单-0v1.md](phase1/docs/step1/Step1实现任务分解清单-0v1.md) 作为冻结边界。实现采用 Python 标准库与 unittest，不使用第三方依赖、隐藏缓存或随机性。

Step 1 运行配置如下：

1. 分割方案固定为 cc4、cc8、whole_grid。
2. 原语范围固定为 copy、translate、rotate、flip、delete、recolor、fill、crop。
3. 关系范围固定为 relative_position 与 alignment；包含、层级、repeat、construct_grid 等能力全部推迟到 Step 2。
4. Layer 3 使用最小 beam 机制：先按轻量 pre_priority 预排序，再截到 STEP1_BEAM_SIZE = 64 个 hypothesis 进入执行评估。
5. pre_priority 在 Step 1 中不是完整 AST 语义分析，而是字符串级 proxy：用 program 文本中的 target=/color= 及符号参数（input_width 等）计数近似 attr_ref_ratio，用分号数（排除 copy block 结构性分隔符）近似 ast_depth。

## 3. 关键实现与收口结果

Step 1 收尾阶段的重点不是继续堆求解率，而是把接口和文档口径收紧到可交接状态。本轮收口完成了以下四项关键工作：

1. 冻结了 Layer 1、Hypothesis、Attribution、SearchStats 的最小接口，并用测试锁定字段集合，避免文档与代码继续漂移。
2. 把 ID 语义明确拆成两层：`alignment_id` 保留 pair 级 provenance，`alignment_family_id` 作为跨 pair 聚合键；原始 Layer 2 候选使用 pair 级 transform/constraint ID，聚合后的候选池再改用 family 级运行时 ID。
3. 把 beam 从“文档已有、代码未接线”的占位状态，收成真实行为：`candidates_evaluated` 现在表示进入最小 beam 后实际执行评估的 hypothesis 数，`beam_saturated` 也具有真实语义。
4. 把 Step 1 的可接受收尾标准写清楚：禁止样例级 ad hoc 特判；若存在任务族级受限 mode，必须显式登记、固定语义、不可任意组合，也不能包装成一般能力。

## 4. 实验结果

截至 2026-04-04，Step 1 的批量运行摘要见 [summary.json](phase1/outputs/step1/reports/summary.json) 与 [summary.md](phase1/outputs/step1/reports/summary.md)，核心结果如下：

1. 训练任务总数：12。
2. 精确求解数：6。
3. 失败归因分布：`NONE = 6`，`ABSTRACTION_FAIL = 6`。
4. 最常被选中的分割方案：`cc4`。
5. 最常被选中的对齐策略：`bipartite`。
6. 平均各层耗时：Layer 1 为 1.167 ms，Layer 2 为 3.5 ms，Layer 3 为 4.917 ms，Layer 4 为 13.333 ms，Layer 5 为 0.0 ms。

从结果看，Step 1 已经稳定跑通最小闭环，但它并没有把剩余 6 个失败任务伪装成“即将通过的小补丁问题”，而是诚实地归因为抽象能力不足。这与 Step 1 的定位一致：当前失败样式主要对应更强对象表示、对象组复制、repeat/tile、层级/包含等 Step 2 能力，而不是继续在 Step 1 内做样例级特判。

## 5. 验收结果

本次验收同时参考运行结果、接口稳定性和测试回归情况。验收结论是：**Step 1 可按“最小闭环已实施冻结”通过验收，但该通过只在 Step 1 的收窄目标下成立，不代表系统已经具备更广泛任务族的一般求解能力。**

通过依据如下：

1. 端到端闭环已经稳定存在：Layer 1 到 Layer 5 可以对 12 个训练任务批量运行，并输出调试产物、Attribution 和汇总报告。
2. 接口已冻结：Layer 1 输出、Hypothesis 五字段结构、Attribution 最小归因结构、SearchStats 字段、pair/family 双层 ID 语义都已经与代码和文档对齐。
3. 遥测已具备解释力：`selected_plan`、`selected_alignment`、`selected_alignment_family`、`selected_program`、`selected_constraints`、`candidates_generated`、`candidates_evaluated`、`beam_saturated` 等关键字段均可追溯。
4. 验证已完成：`python3 -m unittest discover -s phase1/tests/step1` 当前共 71 个测试通过，覆盖 Layer 1-5、runner、接口冻结与 beam/ID 收口行为。
5. 失败表达是诚实的：剩余失败被保留为 `ABSTRACTION_FAIL`，没有通过样例级 ad hoc 或隐性 DSL 扩张去伪造更高成功率。

同时，本报告明确给出未通过项的边界说明：

1. Step 1 未达到 12/12 精确求解。
2. Step 1 不应被描述为通用 DSL、通用关系集或通用搜索框架的完成版。
3. Copy2-6、Center3 及其他需要更强对象表示、对象组复制、repeat/tile、层级/包含能力的样式，应进入 Step 2 处理，而不是继续在 Step 1 内硬补。

## 6. 结论

Step 1 当前最合理的定位，不是“一个低成功率但想继续补丁的半成品”，而是“一个目标收窄后已可冻结的最小结构闭环”。它已经完成了第一阶段最重要的事情：把结构感知、候选生成、假设组装、程序执行、失败归因这条链路跑通，并把关键接口和验收口径收紧到可以作为 Step 2 起点的状态。

因此，建议将 Step 1 作为已验收的冻结基线保存，后续扩展以 Step 2 为主线推进，而不是继续在 Step 1 内追求边界外任务的表面成功率。

与 [第一阶段研究计划-0v1.md](phase1/docs/第一阶段研究计划-0v1.md) 和 [第一阶段算法架构-0v4.md](phase1/docs/第一阶段算法架构-0v4.md) 的当前表述一致，本报告的正式阶段性结论是：截至 2026-04-04，Step 1 已经给出了偏积极但不夸大的信号。它说明这条结构主义路线在“最小闭环验证”层面能够工作，当前也没有出现需要退出第一阶段或推翻路线的证据；但这还不是第一阶段整体成功的最终证明。更合理的工程决策是把 Step 1 作为已实施冻结的基线保存，并以剩余 `ABSTRACTION_FAIL` 所指向的能力缺口为入口，进入 Step 2 的单任务求解器加固。
