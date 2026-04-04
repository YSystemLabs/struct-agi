# 第一阶段 Step 1 实现设计

> 版本：v0.1
>
> 状态：已实施冻结
>
> 作用：定义 Step 1 最小闭环验证的实现顺序、模块职责、测试策略与验收门槛。

## 1. 文档定位

本文档是 Step 1 的实现设计正文，只回答“怎么实现最小闭环”。

本文档不重新定义 Step 1 的任务范围、最小接口和冻结边界。这些内容以 [Step1最小接口与任务清单附录-0v1.md](phase1/docs/step1/Step1最小接口与任务清单附录-0v1.md) 为准。

本文档与以下文档的关系如下：

| 文档 | 作用 |
| --- | --- |
| [第一阶段研究计划-0v1.md](phase1/docs/第一阶段研究计划-0v1.md) | 定义研究问题、成功标准与退出条件 |
| [第一阶段算法架构-0v4.md](phase1/docs/第一阶段算法架构-0v4.md) | 定义完整五层架构与长期接口 |
| [Step1最小接口与任务清单附录-0v1.md](phase1/docs/step1/Step1最小接口与任务清单附录-0v1.md) | 冻结 Step 1 的实现边界 |
| 本文档 | 规定 Step 1 的实现顺序、模块拆分、测试与验收 |

## 2. Step 1 实现目标

Step 1 的唯一目标是：

> 在 Copy1-6 与 Center1-6 这 12 个训练任务上，跑通一个可审计的最小闭环，使系统能够从 train pairs 中产生候选结构、筛选假设、执行程序并输出基础归因。

Step 1 不追求：

1. 覆盖全部原语或全部关系类型。
2. 引入排序模型、知识状态写回或三阶段知识重写。
3. 在 ConceptARC 全集或 ARC-AGI-2 上报告主结果。
4. 通过样例级特判堆出成功率。

### 2.1 当前收尾范围裁剪

在当前实现状态下，Step 1 的剩余工作范围进一步收缩为：**只继续处理 Center5 与 Center6**。

其余尚未精确求解的任务，当前阶段不再继续追，原因如下：

1. `Center5` 与 `Center6` 仍落在 Step 1 已放开的能力边界内：它们都可以继续用现有 `translate` / `delete`、现有 selector（`smallest_object`、`rare_color_object`）以及现有锚点参数（`to_input_center_*`、`to_largest_object_center_*`）来表达；若当前 plan 把稀有色源图样并进大对象或把锚点结构切成许多碎片，则允许像 Center4 一样补一个固定语义的受限 `translate` mode，而不新增 primitive、分割方案或关系类型。
2. `Center3` 暂停到 Step 2：它需要更强的层级/嵌套感知，而 Step 1 只允许 `cc4`、`cc8`、`whole_grid` 三种分割，也不实现包含与层级关系。继续追它会把 Step 1 推向 `nested` / `bbox` / containment 一类扩展。
3. `Copy5` 与 `Copy6` 暂停到 Step 2：它们的核心规则是块级重复、行列级重复或带分隔的重复展开，已经逼近 `repeat` / `tile` / `construct_grid` 一类能力，不应在 Step 1 里用隐性 DSL 扩张去硬做。
4. `Copy3` 与 `Copy4` 暂停到 Step 2：它们要求的不是单对象、单锚点、单次搬运，而是更接近“对象组复制”或“多锚点放置”的程序模式。正文已明确 Step 1 不把现有能力扩成多锚点广播或一般 repeat。
5. `Copy2` 暂停到 Step 2：当前问题已经触到对象表示本身。要把一个多色连通图样完整复制到新位置，需要比 Step 1 当前最小对象表示更强的内部颜色结构保真；这不再是简单补 selector 或补一个符号参数的问题。

这一定义的含义不是“这些任务永远不做”，而是：**在 Step 1 中不再为它们扩边界**。它们保留为 Step 2 的明确入口样例。

## 3. 实现原则

Step 1 的实现遵循以下四条原则：

1. 先保证可审计，再追求求解率。任何模块若只能通过隐藏状态或临时特判工作，视为未完成。
2. 先保证单层输出稳定，再做端到端联调。禁止在 Layer 1、Layer 2 尚不稳定时直接堆 Layer 3-5 的补丁。
3. 先做主干最小子集，再做局部增强。所有超出附录冻结范围的能力一律推迟到 Step 2。
4. 运行日志必须和实现同步落地。Step 1 不是“先写完代码再补可观测性”，而是边实现边记录遥测和归因证据。

## 4. 代码组织建议

为避免把核心实现继续堆到 scripts 目录，Step 1 正文建议在 phase1 下新增 src 目录，结构如下：

```text
phase1/
├── src/
│   └── step1/
│       ├── __init__.py
│       ├── config.py                 # Step 1 冻结配置、任务清单、常量
│       ├── data/
│       │   ├── __init__.py
│       │   ├── loader.py             # ConceptARC 任务加载与 train/test 访问
│       │   └── models.py             # Task / Pair / Grid 等基础数据结构
│       ├── layer1/
│       │   ├── __init__.py
│       │   ├── perception.py         # cc4 / cc8 / whole_grid 分割主入口
│       │   ├── objects.py            # Object 构建与属性提取
│       │   └── relations.py          # relative_position / alignment
│       ├── layer2/
│       │   ├── __init__.py
│       │   ├── alignment.py          # 一对一对象对齐
│       │   ├── diff.py               # 差异类型识别
│       │   ├── constraints.py        # Step 1 最小约束提取
│       │   └── sketches.py           # CandidateSet / ProgramSketch 生成
│       ├── layer3/
│       │   ├── __init__.py
│       │   ├── hypothesis.py         # Hypothesis 组装
│       │   ├── scoring.py            # L(h) / mismatch / Score(h)
│       │   └── selector.py           # 两阶段筛选与等价类归并
│       ├── layer4/
│       │   ├── __init__.py
│       │   ├── dsl.py                # Step 1 DSL 子集与解析表示
│       │   ├── executor.py           # 程序执行
│       │   └── render.py             # output 网格渲染
│       ├── layer5/
│       │   ├── __init__.py
│       │   ├── verify.py             # 像素级验证与约束检查
│       │   └── attribution.py        # 最小归因输出
│       ├── runner/
│       │   ├── __init__.py
│       │   ├── task_runner.py        # 单任务端到端运行
│       │   └── batch_runner.py       # Step 1 批量运行入口
│       └── utils/
│           ├── __init__.py
│           ├── timing.py             # 各层耗时统计
│           ├── ids.py                # plan_id / alignment_id / transform_id 生成
│           └── debug_dump.py         # 调试输出与中间产物落盘
└── outputs/
    └── step1/
        ├── debug/                    # 中间结构与可视化调试输出
        └── reports/                  # 批量运行后的统计结果
```

此结构的目的不是追求“工程感”，而是保证 Layer 1 到 Layer 5 的职责边界在代码里也可见。

## 5. Step 1 端到端流程

单个任务的执行流程固定如下：

1. 读取任务 JSON，解析 train pairs 与 test pair。
2. 对每个 train input 与 train output 独立运行 Layer 1，得到 PerceptionOutput。
3. 对每个分割方案运行 Layer 2：生成对齐、最小约束、ProgramSketch 候选。
4. 将所有 CandidateSet 输入 Layer 3，组装并筛选最优 Hypothesis。
5. 用 Layer 4 将最优 Hypothesis 应用于 test input，得到候选 output。
6. 用 Layer 5 对 train 上的解释力做验证，并对最终求解结果输出归因。
7. 落盘 Attributions、timing、选中的 plan/alignment/program/constraints 和必要调试产物。

Step 1 不允许任何阶段内写回。每个任务独立运行，不共享成功假设，不共享排序模型状态。

## 6. 各层实现设计

### 6.1 Layer 1：结构感知层

Step 1 的 Layer 1 只做三件事：

1. 生成 cc4、cc8、whole_grid 三个分割方案。
2. 为每个对象提取最小属性集合。
3. 为每个方案提取 relative_position 与 alignment 两类 pair relation。

#### 6.1.1 输入输出

- 输入：单张网格。
- 输出：PerceptionOutput。

#### 6.1.2 最小属性集合

每个对象至少包含以下属性：

| 属性 | 用途 |
| --- | --- |
| dominant_color | recolor、对齐匹配、颜色一致性检查 |
| area | 排序、调试、简单形状判别 |
| height / width | translate 参数绑定、形状匹配 |
| center_row / center_col | Center 任务的关键定位特征 |
| bbox | 渲染、相对位置、调试 |

Step 1 不要求 `is_rectangular`、`color_hist`、层级属性等完整扩展字段。

#### 6.1.3 关系提取规则

- `relative_position`：对对象对计算上/下/左/右/对角方位。
- `alignment`：对对象对判断同一行、同一列、中心线对齐。

Step 1 不从 Layer 1 直接输出颜色映射和尺寸映射 relation；这些信息通过对象属性在 Layer 2/3 中使用。

#### 6.1.4 完成标准

Layer 1 完成，必须满足：

1. 同一输入在同一分割策略下结果确定。
2. 对象 ID 在单次运行内稳定唯一。
3. 三个分割方案均能序列化为调试输出。

### 6.2 Layer 2：候选生成层

Step 1 的 Layer 2 是最关键的高风险层。它首次把单图结构提升为 input-output pair 上的候选解释。

#### 6.2.1 对齐子模块

Step 1 只允许一对一对象对齐，执行顺序如下：

1. 像素重合匹配。
2. 颜色+形状匹配。
3. 最优二部匹配。

若某个 plan 下三种方法全部失败，则丢弃该 plan。若所有 plan 都失败，则任务最终归为 `PERCEPTION_FAIL`。

实现注记：Step 1 当前代码把对齐标识拆成两层。`alignment_id = "{plan_id}:{method}:{pair_index}"` 表示单个 train pair 上的原始对齐；`alignment_family_id = "{plan_id}:{method}"` 表示跨全部 train pair 聚合后的对齐家族。进入 Layer 3 之前，代码先按 `alignment_family_id` 聚合同一家族的变换和约束证据；但 `size_rule:*` 不允许在 family 级被一次性压成所有 program 共用的单条规则，而必须在组装具体 hypothesis 时，再投影到该 program 的 `applicable_pairs` 上决定。进入筛选层后，raw provenance 和 family 级绑定键都以独立字段保留。

补充：Step 1 当前实现也把 transform / constraint 的子 ID 拆成两层。原始 Layer 2 候选使用 pair 级 `alignment_id` 生成 `transform_id` / `constraint_id`，用于保留 provenance；跨 train 聚合后的下游候选则改用 `alignment_family_id` 重新编号，作为 family 级候选池中的稳定运行时 ID。这两层语义必须同时保留，不能再由同名字段隐式混用。

#### 6.2.2 差异识别

Step 1 只关心以下差异类型：

| 差异类型 | 对应候选原语 |
| --- | --- |
| 新增对象 | copy |
| 中心填充 / 空洞填充 | fill |
| 消失对象 | delete |
| 位置变化 | translate |
| 形状变化 | rotate / flip |
| 颜色变化 | recolor |
| 中心提取 / 中心裁剪 | crop |

Step 1 不处理：merge、split、tile、construct_grid 以及依赖一般布局规划的尺寸变化；但允许由 copy/translate 导致的有限画布扩张，以及由 crop 导致的有限中心裁剪。

#### 6.2.3 最小约束提取

Step 1 只提取：

1. 有限输出尺寸规则：`preserve_input_size`、`fit_transformed_extent`、`crop_selected_bbox`、`crop_center_cell`。
2. 颜色映射一致性。
3. 相对位置约束。

`weak` 约束允许为空，且不阻塞 Step 1 的筛选流程。

#### 6.2.4 ProgramSketch 范围

Step 1 的 ProgramSketch 只支持：

- 单步原语；
- 最多两步序列复合；
- `copy ; on_copy:` / `copy ; on_original:` 焦点块；
- 受限 `fill` 与受限 `crop`；
- 参数孔位 `?`；
- 不支持控制流。

对当前 Step 1 任务集，Layer 2 必须把以下两类模式视为显式候选，而不是“可选优化”：

1. 对 Copy 类任务，允许生成 `copy ; on_copy: translate(...)` 形式的重复候选，用于表达“保留原对象，并把副本按对象宽度、高度或已观测相对位移移动到新位置”。
2. 对 Center 类任务，允许生成 `fill[target=..., mode=center_cell]` 形式的中心单元填充候选；这属于受限 `fill` 的标准覆盖面，不引入新原语。

进一步约束：Copy 类位移参数不允许在 Step 1 中扩展成一般模板表达式；只允许绑定到有限符号表中的受限引用：`input_width`、`input_height`、`object_width`、`object_height` 及其带符号版本。若某个 train pair 的观测位移正好等于这些受限引用之一，Layer 2 应优先产出对应的符号参数版本，便于跨 pair 聚合成同一程序。

对当前剩余 Step 1 任务，还允许两类受限 selector / 参数化扩展，且都仍视为 Step 1 内能力，而不是 Step 2：

1. `center_object`：用于把 `crop` / `delete` 绑定到“当前 plan 中最接近输入画布中心的对象”。
2. `smallest_object` / `rare_color_object` 与 `to_input_center_*` / `to_largest_object_center_*`：用于表达“把一个单源对象一次性搬到输入中心或最大对象中心”。

补充：对 Center4 一类“删除输入中心处的同色连通域，但该连通域未必在当前分割 plan 中成为独立对象”的任务，Step 1 允许使用受限形式 `delete[target=all,mode=input_center_component]`。它不引入新原语，只是 `delete` 的一个固定 mode，语义为“删除输入画布中心单元所在的 4 邻域同色连通域”。

补充：对 Center5 / Center6 一类“真正需要搬运的是全局稀有色图样，但当前 plan 可能把它并进单个多色对象，或把目标结构切成许多同面积碎片”的任务，Step 1 允许使用受限形式 `translate[target=all,mode=rare_color_motif_to_largest_component_center]`。它不引入新 primitive，只是 `translate` 的一个固定 mode，语义为“抽取输入中全局最稀有非零颜色的全部像素图样，并把该图样的 bbox 中心平移到输入里最大 8 邻域非零连通块的 bbox 中心”。这仍然是单次搬运，不放开对象组复制、一般 repeat 或可组合规划。

边界约束：这仍然只是单对象、单锚点、单次搬运；不允许扩展成多锚点广播、一般 repeat、`ForEach` 或 `group_by`。

当前收尾解释：因此，Center5 与 Center6 仍允许继续补候选，前提只限于两类动作：一是补现有 selector 与现有锚点参数的缺失组合；二是补这种固定语义、不可组合扩张的受限 mode。Copy3 / Copy4 / Copy5 / Copy6 若需要对象组复制、块级重复或一般 repeat，则一律停止，转入 Step 2。

即使 Layer 3 完成了参数绑定，Step 1 最终输出到 Layer 4 的 `program` 也仍然必须受附录中的 Step 1 DSL 子集约束，不允许回升到包含 `ForEach`、`If` 的完整 Program。

#### 6.2.5 完成标准

Layer 2 完成，必须满足：

1. 每个 CandidateTransform 都可追溯到唯一 `alignment_id`。
2. 每个 CandidateConstraint 都可追溯到唯一 `alignment_id`。
3. 对齐失败、候选为空、约束为空三种情况均有明确日志。

补充：跨 train 聚合完成后，进入筛选层的下游候选保留 pair 级 `alignment_id`，并新增显式 `alignment_family_id` 作为 family 级绑定键。

### 6.3 Layer 3：任务相关结构筛选层

Step 1 的 Layer 3 只实现主架构中最小必要版本。

#### 6.3.1 Hypothesis 组装

搜索单元固定为：

```text
Hypothesis = (plan_id, alignment_id, alignment_family_id, constraint_subset, program)
```

禁止跨对齐混搭。所有 program 和 constraint 必须绑定同一个对齐绑定键。在当前 Step 1 代码里，这个绑定键显式记录在 `alignment_family_id`；`alignment_id` 只保留原始 provenance 语义。

补充约束：family 级候选池只负责收集证据，不负责替所有 program 预先决定唯一 `size_rule:*`。实际组装单个 hypothesis 时，必须先把约束投影到该 program 的 `applicable_pairs`，再决定其强约束中的唯一 `size_rule:*`；若同一 program 在相关 pair 上观测到多个 `size_rule:*`，允许拆成多个 hypothesis 交由 Layer 3 筛选，而不是在 Layer 2/3 交界处粗暴合并。

说明：前一轮关于 size-rule / program 绑定粒度的修正仍然保留，不需要回滚。它解决的是 family 级错误绑定问题；本轮补的是 Center4 仍然缺失的候选表达能力，两者职责不同。

#### 6.3.2 筛选逻辑

Step 1 采用两阶段评分：

1. 优先找 train 上 100% 像素匹配的假设。
2. 若不存在，则按 `mismatch_sum + lambda * L(h)` 选最优回退假设。

这里的“同一假设”允许包含上述受限符号参数；Step 1 希望通过这类有限参数化把多个 train pair 上的同构 Copy 规则聚合到一个 program，而不是把每个 pair 的 dx/dy 常量硬编码成彼此不同的程序文本。

补充约定：在第 2 阶段允许加入极小、固定、显式记录到调试输出中的启发式罚分，但该罚分只能用于压制明显退化的候选，不得改写主排序框架。当前 Step 1 唯一允许的这类启发式，是对“语义空转的 copy 块”施加小额罚分，例如 `copy ; on_copy: ; on_original:` 这类既不改变副本也不改变原对象、且 train 上仍非精确匹配的候选。

#### 6.3.3 等价类归并

Step 1 保留等价类归并，但只要求最小实现：

1. 按 train 输出向量哈希分组。
2. 每组保留描述长度最短的代表元。
3. 保留全部等价类成员，并记录等价类大小与代表元约束集，供调试与后续扩展。
4. 若第 2 阶段回退评分使用了允许范围内的小额启发式罚分，必须把罚分来源与数值一并记录到 selector 调试结果中。

Step 1 的搜索阶段仍按主架构使用代表元参与评估，但 Step 1 不强制实现主架构中的完整“等价类并行执行 + 显式 tie-break”测试语义。正文实现以附录中的保守边界为准：`weak` 可为空，test 阶段不因弱约束 tie-break 缺失而阻塞；但等价类成员、代表元、等价类大小和代表元约束集必须保留，不能在 Step 1 中被语义删除。

#### 6.3.4 预排序

Step 1 不启用排序模型，`pre_priority` 只使用两个**字符串级代理特征**：

1. `attr_ref_ratio`：按 program 文本中 `target=` 与 `color=` 的出现次数，相对 token 总数做近似。
2. `ast_depth`：按 program 文本中的分号层数 `;` 加 1 做近似。

Layer 3 先按该轻量 `pre_priority` 对 hypothesis 预排序，再取前 `STEP1_BEAM_SIZE = 32` 个 hypothesis 进入 train 执行评估；若发生截断，`search_stats.beam_saturated = true`。这不是完整的 AST / AttrRef 语义分析，只是 Step 1 收尾阶段可审计、低成本的 proxy。

必要时可加入极少量固定启发式，但必须在代码与日志里显式声明。

#### 6.3.5 完成标准

Layer 3 完成，必须满足：

1. 能输出唯一最优 Hypothesis 或明确的回退 Hypothesis。
2. 能给出 `selected_plan`、`selected_alignment`、`selected_program`、`selected_constraints`。
3. 能记录 `candidates_generated`、`candidates_evaluated` 与 `beam_saturated`；其中 `candidates_evaluated` 指进入 Step 1 最小 beam 后实际执行评估的 hypothesis 数。

### 6.4 Layer 4：求解层

Step 1 的 Layer 4 只实现路径 A，即确定性程序执行。

#### 6.4.1 执行范围

支持的执行原语仅限：

- copy
- translate
- rotate
- flip
- delete
- recolor
- fill
- crop

Step 1 的可执行程序仍然只允许落在附录冻结的 Step 1 DSL 子集内，不实现 `ForEach`、`If`、`group_by`、`merge`、`partition`、`construct_grid` 等完整 DSL 能力。

#### 6.4.2 渲染规则

Step 1 必须实现以下渲染规则：

1. 当输出尺寸规则为 `preserve_input_size` 时，输出画布尺寸保持与输入一致。
2. 当输出尺寸规则为 `fit_transformed_extent` 时，输出画布取执行后对象像素并集的最小外接矩形。
3. 当输出尺寸规则为 `crop_selected_bbox` 或 `crop_center_cell` 时，输出直接取 crop 结果，不再沿用输入画布。
4. 背景色先填充，再叠加对象。
5. 对象覆盖顺序按面积从大到小；同面积冲突按程序顺序后写覆盖前写。
6. 仅在 `preserve_input_size` 模式下对越界像素做截断；其余模式优先通过尺寸推断容纳结果。

#### 6.4.3 完成标准

Layer 4 完成，必须满足：

1. 所有启用原语在独立单测下有确定性输出。
2. `copy` 的原件/副本焦点语义与主架构保持一致。
3. 四类输出尺寸规则都能回写为标准 ARC 网格格式。

### 6.5 Layer 5：验证与归因层

Step 1 的 Layer 5 只运行模式 A。

#### 6.5.1 必做验证

1. 像素级精确匹配。
2. 最小约束检查。
3. 失败归因标签输出。

#### 6.5.2 归因范围

Step 1 只要求稳定输出以下主类型：

- `NONE`
- `PERCEPTION_FAIL`
- `SELECTION_FAIL`
- `ABSTRACTION_FAIL`
- `EXECUTION_FAIL`

`failure_confidence`、`expansion_hint` 等更细粒度结构不是 Step 1 的强制项。

#### 6.5.3 完成标准

Layer 5 完成，必须满足：

1. 每个任务都产出 Attribution。
2. 失败任务不允许只返回空结果，必须带 `failure_type`。
3. 归因输出可与调试产物一一对应。

## 7. 实现顺序

Step 1 的推荐实现顺序固定如下：

1. `data` 和 `config`：冻结任务清单、基础数据结构、批量运行入口。
2. Layer 1：先让三种分割方案和对象属性稳定输出。
3. Layer 4：先做最小 DSL 执行器与渲染，避免 Layer 3 无法评估候选。
4. Layer 2：接入一对一对齐、差异识别、最小约束和 ProgramSketch。
5. Layer 3：接入 Hypothesis 组装、评分、等价类归并和最优选择。
6. Layer 5：补齐像素验证、约束检查与基础归因。
7. `runner`：完成单任务与批量执行脚本。

之所以先做 Layer 4 再做完整 Layer 3，是因为 Step 1 的筛选质量最终依赖真实执行结果，而不是只依赖草图静态分析。

## 8. 测试与验证策略

### 8.1 单层测试

每层至少需要以下最小测试：

| 层 | 最小测试 |
| --- | --- |
| Layer 1 | 单网格分割结果稳定，对象数和 bbox 可人工验证 |
| Layer 2 | 一对一对齐结果稳定，alignment_id 绑定不丢失 |
| Layer 3 | 对固定候选集输出稳定最优 Hypothesis |
| Layer 4 | 八个原语各有独立执行测试，并覆盖尺寸扩张与中心裁剪 |
| Layer 5 | 成功/失败样例都能产出非空 Attribution |

### 8.2 端到端测试

端到端测试分三轮推进：

所有 smoke test、联调和调参都只能使用 Copy1-6 与 Center1-6 这 12 个训练任务；诊断任务在 Step 1-2 全程不可见。

1. 先用 `Copy1`、`Center1`、`Center2` 做 smoke test，分别覆盖画布扩张、定点填充和中心裁剪。
2. 再扩到 Copy1-6。
3. 最后扩到 Center1-6 与全部 12 个任务。

每扩一轮，必须输出：

1. 精确求解数。
2. 失败类型分布。
3. 每层耗时统计。
4. 最常被选中的分割方案与对齐策略。

当前收尾阶段不再把上述扩轮目标用于 `Copy2`、`Copy3`、`Copy4`、`Copy5`、`Copy6`、`Center3` 的继续优化；这些任务只保留归因与调试产物，不再作为 Step 1 的待攻坚目标。

### 8.3 人工审查

Step 1 结束前，至少人工抽查：

抽查样本同样只能来自这 12 个训练任务，不得使用诊断任务补充成功样例或失败样例。

1. 3 个成功任务。
2. 3 个失败任务。

抽查内容必须包括：

1. Layer 1 对象图是否合理。
2. Layer 2 对齐是否明显错配。
3. Layer 3 选中的 program 是否可读。
4. Layer 5 的 failure_type 是否与调试证据一致。

## 9. 遥测与调试产物

Step 1 每个任务至少落盘两类产物：

1. 机器可读结果：Attribution JSON、timing JSON、selected hypothesis 摘要；其中必须包含 `selected_constraints` 与 `search_stats`。
2. 人类可读调试产物：对象分割可视化、对齐可视化、选中程序文本。

推荐输出目录：

```text
phase1/outputs/step1/
├── debug/
│   └── <task_id>/
│       ├── layer1.json
│       ├── layer2.json
│       ├── selected_hypothesis.json
│       └── attribution.json
└── reports/
    ├── summary.json
    └── summary.md
```

## 10. Step 1 验收门槛

Step 1 完成，不以“代码写完”为准，而以以下四条同时满足为准：

1. 五层最小闭环全部可运行。
2. 12 个训练任务中精确求解数不少于 9 个。
3. 未解任务均有非空、可读且归因合理的输出。
4. 系统未依赖样例级 ad-hoc 特判；若存在为某个任务族补入的受限 mode，必须在正文和附录中显式写清其固定语义、触发边界与非目标能力，不能把它伪装成已经获得的一般统一抽象。

若第 4 条不满足，即使成功率看起来够高，也不视为 Step 1 完成。

### 10.1 当前收尾验收

在完成 Center4 后，Step 1 的**当前收尾验收**改为以下约束：

1. 后续实现只允许继续面向 `Center5`、`Center6` 做收尾，不再把 `Copy2`、`Copy3`、`Copy4`、`Copy5`、`Copy6`、`Center3` 作为 Step 1 攻坚目标。
2. 对 `Center5`、`Center6` 的任何修改，都不得引入 Step 2 能力：不得新增分割方案、不得新增关系类型、不得新增 primitive、不得把单对象语义扩成对象组复制或一般 repeat。
3. 本轮收尾的理想结果是 `Center5`、`Center6` 都达到精确求解，使 batch 的 `exact_solved` 从 4 提升到至少 6。
4. 若在不突破 Step 1 边界的前提下，`Center5`、`Center6` 仍不能精确求解，则 Step 1 视为到达当前边界，应停止继续扩张，并把剩余问题整体移交 Step 2，而不是继续为单题放宽 DSL 或感知能力。
5. 因此，Step 1 的收尾验收不仅检查“这两题是否被解出”，还检查“是否通过守边界的方式解出”。若解题依赖了正文和附录未放开的能力，则该结果不计入 Step 1 验收。
6. 即使结果计入 Step 1 验收，也必须如实区分两件事：一是“没有使用样例级 ad-hoc 特判”；二是“是否仍使用了任务族级、固定语义、已文档化的受限 mode”。后者可以在当前收尾阶段被接受，但不得被表述成已经得到更一般、更统一的最小抽象。

## 11. 退出条件

出现以下任一情况，Step 1 应暂停扩展并回到设计层修订：

1. Layer 1 输出不稳定，导致同一输入多次运行结果不同。
2. Layer 2 一对一对齐在大多数任务上不可靠。
3. Layer 3 的候选评分严重依赖手工特判。
4. Layer 4 的 DSL 语义与主架构不一致。
5. Layer 5 的归因标签无法和实际调试证据对齐。

## 12. 与后续 Step 的衔接

Step 1 完成后，允许进入 Step 2 的前提不是“想扩就扩”，而是以下接口已经稳定：

1. Layer 1 输出 schema 稳定。
2. Alignment 与 `alignment_id` 绑定稳定。
3. Hypothesis 五字段结构稳定。
4. Attribution 最小 schema 稳定。
5. 各层 timing 与 search_stats 可持续记录。

只有这些接口稳定，Step 2 才值得在其上增加新原语、新分割策略和更丰富的约束。
