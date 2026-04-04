# 第一阶段 Step 1 最小接口与任务清单附录

> 版本：v0.1
>
> 状态：已实施冻结
>
> 作用：为 Step 1 最小闭环验证冻结任务边界、最小接口、对齐白名单与运行遥测，消除实现歧义。

## 1. 文档定位

本附录不是新的算法设计文档，而是 [第一阶段算法架构-0v4.md](phase1/docs/第一阶段算法架构-0v4.md) 中 Step 1 的实现冻结清单。

本附录只回答四类问题：

1. Step 1 到底跑哪些任务。
2. Step 1 到底实现哪些最小接口字段。
3. Step 1 的对齐与约束到底允许到什么程度。
4. Step 1 运行时到底必须记录哪些遥测信息。

凡本附录未明确放开的能力，默认不属于 Step 1。

## 2. Step 1 冻结范围

Step 1 只服务于“最小闭环验证”，不服务于覆盖率，不服务于持续学习，不服务于完整原语库验证。

### 2.1 数据范围

Step 1 只使用 ConceptARC 的 Copy 与 Center 两个概念组训练任务。

训练任务清单如下：

| 概念组 | 任务 ID | 路径 |
| --- | --- | --- |
| Copy | Copy1 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy1.json |
| Copy | Copy2 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy2.json |
| Copy | Copy3 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy3.json |
| Copy | Copy4 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy4.json |
| Copy | Copy5 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy5.json |
| Copy | Copy6 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy6.json |
| Center | Center1 | phase1/datasets/raw/ConceptARC/corpus/Center/Center1.json |
| Center | Center2 | phase1/datasets/raw/ConceptARC/corpus/Center/Center2.json |
| Center | Center3 | phase1/datasets/raw/ConceptARC/corpus/Center/Center3.json |
| Center | Center4 | phase1/datasets/raw/ConceptARC/corpus/Center/Center4.json |
| Center | Center5 | phase1/datasets/raw/ConceptARC/corpus/Center/Center5.json |
| Center | Center6 | phase1/datasets/raw/ConceptARC/corpus/Center/Center6.json |

诊断任务固定如下，Step 1-2 全程不可见：

| 概念组 | 任务 ID | 路径 |
| --- | --- | --- |
| Copy | Copy7 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy7.json |
| Copy | Copy8 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy8.json |
| Copy | Copy9 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy9.json |
| Copy | Copy10 | phase1/datasets/raw/ConceptARC/corpus/Copy/Copy10.json |
| Center | Center7 | phase1/datasets/raw/ConceptARC/corpus/Center/Center7.json |
| Center | Center8 | phase1/datasets/raw/ConceptARC/corpus/Center/Center8.json |
| Center | Center9 | phase1/datasets/raw/ConceptARC/corpus/Center/Center9.json |
| Center | Center10 | phase1/datasets/raw/ConceptARC/corpus/Center/Center10.json |

### 2.2 分割方案范围

Step 1 只启用以下三种分割方案：

| method | 含义 |
| --- | --- |
| cc4 | 按颜色 4-连通分量分割 |
| cc8 | 按颜色 8-连通分量分割 |
| whole_grid | 将整张网格视为单一对象 |

以下方案推迟到 Step 2：bbox、bg_fg、repeat、nested。

### 2.3 Step 1 最小关系与属性范围

Step 1 的最小关系与属性范围固定如下。这是 Step 1 针对 Copy / Center 任务族的实现子集，不改写主架构中的完整关系表。

| 类别 | Step 1 是否实现 | 说明 |
| --- | --- | --- |
| 相对位置 | 是 | 上下左右、对角方位 |
| 对齐 | 是 | 共享行、共享列、中心线对齐 |
| 邻接 | 否 | 推迟到 Step 2 |
| 包含 | 否 | 推迟到 Step 2 |
| 对称 | 否 | 推迟到 Step 2 |
| 颜色映射 | 否 | Step 1 不实现为独立 pair relation |
| 尺寸映射 | 否 | Step 1 不实现为独立 pair relation |
| 条件依赖/计数/层级 | 否 | 推迟到 Step 2 之后 |

补充：Step 1 仍输出 dominant_color、height、width、area 等对象属性，用于对齐、候选生成与约束检查；但不把颜色映射、尺寸映射实现为独立关系类型。

### 2.4 原语范围

Step 1 只允许以下原语进入候选与执行流程：

| 原语 | Step 1 状态 |
| --- | --- |
| copy | 启用 |
| translate | 启用 |
| rotate | 启用 |
| flip | 启用 |
| delete | 启用 |
| recolor | 启用 |
| fill | 启用 |
| crop | 启用 |
| scale | 禁用 |
| extend_to_boundary | 禁用 |
| conditional_map | 禁用 |
| merge | 禁用 |
| sort | 禁用 |
| group_by | 禁用 |
| tile | 禁用 |
| construct_grid | 禁用 |
| partition | 禁用 |

### 2.5 DSL 子集

Step 1 不实现完整 DSL，只实现完整 DSL 的严格子集。

```text
Program_step1   ::= Transform | Transform ";" Transform
Transform       ::= PrimitiveOp Args
                  | "copy" ";" FocusBlock

FocusBlock      ::= FocusClause
                  | FocusClause ";" FocusClause

FocusClause     ::= "on_copy:" Transform
                  | "on_original:" Transform

PrimitiveOp     ::= "translate" | "rotate" | "flip" | "delete" | "recolor" | "fill" | "crop"
```

说明：Step 1 沿用主架构中的 copy 特殊语义；copy 不属于 PrimitiveOp，而是通过专用产生式 "copy" ";" FocusBlock 引入。

补充：Step 1 中的 `fill` 与 `crop` 也是受限版本，而不是主架构中的完全一般形式。`fill` 只用于中心单元或单一封闭空洞的定点填充；`crop` 只用于裁剪中心单元或中心对象的 bbox，不放开任意区域拼装。

进一步约束：对于当前 Step 1 固定任务集，`fill(mode=center_cell)` 必须被视为受限 `fill` 的标准实例，供候选生成层显式枚举；它不是新原语，也不是 Step 2 才引入的扩展能力。类似地，`copy ; on_copy: translate(...)` 必须被视为 copy 特殊语义下的标准两步模式，用于表达有限重复，而不是一般循环构造。

同样地，`delete(mode=input_center_component)` 也属于受限 `delete` 的标准实例，语义固定为“删除输入画布中心单元所在的 4 邻域同色连通域”。它不新增 primitive，只补一个与当前任务集相匹配的固定 mode。

同样地，`translate(mode=rare_color_motif_to_largest_component_center)` 也属于受限 `translate` 的标准实例，语义固定为“抽取输入中全局最稀有非零颜色的全部像素图样，并把该图样的 bbox 中心平移到输入中最大 8 邻域非零连通块的 bbox 中心”。它不新增 primitive，只补一个与当前任务集相匹配的固定 mode，也不放开对象组复制、一般 repeat 或可编排的多步布局规划。

参数约束：Step 1 的 `translate.dx` / `translate.dy` 除整数常量外，只允许使用有限符号表：`input_width`、`input_height`、`object_width`、`object_height`、`to_input_center_dx`、`to_input_center_dy`、`to_largest_object_center_dx`、`to_largest_object_center_dy` 及其带符号版本。这里 `input_*` 指当前输入画布尺寸，`object_*` 指当前被作用对象的 bbox 尺寸；`to_input_center_*` 表示把当前对象中心移动到输入画布中心所需位移；`to_largest_object_center_*` 表示把当前对象中心移动到当前 plan 中最大对象中心所需位移。Step 1 不允许组合表达式、算术树或用户自定义参数名。

目标选择约束：Step 1 的 `target` 除显式 `ObjectID` 与 `all` 外，只允许使用有限选择器 `center_object`、`smallest_object`、`rare_color_object`。其中 `center_object` 指 bbox 中心最接近输入画布中心的对象；`smallest_object` 指面积最小对象；`rare_color_object` 指 `dominant_color` 在当前 plan 中出现频次最低的对象。以上选择器都必须使用固定 tie-break，不能依赖样例级特判。

Step 1 明确不实现：ForEach、If、group_by、merge、partition、construct_grid。

## 3. Step 1 最小接口字段清单

以下接口不是未来完整 schema 的替代品，而是完整 schema 的 Step 1 子集。

### 3.1 Layer 1 输出

```text
PerceptionOutput = {
  segmentation_plans: [SegmentationPlan],
}

SegmentationPlan = {
  plan_id: str,
  method: "cc4" | "cc8" | "whole_grid",
  objects: [Object],
  relations: [(ObjectID, ObjectID, Relation)],
}

Object = {
  id: str,
  pixels: set[(row, col)],
  bbox: (min_row, min_col, max_row, max_col),
  attrs: {
    dominant_color: int,
    color: int,
    area: int,
    height: int,
    width: int,
    center_row: float,
    center_col: float,
    canvas_height: int,
    canvas_width: int,
  },
}
```

Step 1 中 `relations` 只强制要求输出 `relative_position` 与 `alignment` 两类 pair relation；颜色和尺寸相关信息通过对象 attrs 提供，用于 Step 1 的最小候选生成与约束检查。

### 3.2 Layer 2 对齐输出

```text
Alignment = {
  alignment_id: str,                         -- pair 级原始对齐 ID = "{plan_id}:{method}:{pair_index}"
  alignment_family_id: str,                  -- family 级对齐键 = "{plan_id}:{method}"
  matched_pairs: [(InputObjectID, OutputObjectID, match_score)],
  unmatched_input: [InputObjectID],
  unmatched_output: [OutputObjectID],
  merge_groups: [],
  split_groups: [],
}
```

Step 1 约束：`merge_groups` 与 `split_groups` 必须恒为空列表。

补充：Step 1 当前实现显式使用 `alignment_family_id` 把多个 train pair 上同方法的原始对齐证据聚合到同一个下游候选池。

### 3.3 Layer 2 候选集输出

```text
CandidateSet = {
  plan_id: str,
  candidate_alignments: [Alignment],
  candidate_transforms: [CandidateTransform],
  candidate_constraints: [CandidateConstraint],
}

CandidateTransform = {
  transform_id: str,
  alignment_id: str,                         -- 原始 provenance 对齐 ID
  alignment_family_id: str,                  -- family 级绑定键
  program: ProgramSketch,
  applicable_pairs: [int],
  match_score: float,
}

CandidateConstraint = {
  constraint_id: str,
  alignment_id: str,                         -- 原始 provenance 对齐 ID
  alignment_family_id: str,                  -- family 级绑定键
  predicate: str,
  holds_in: [int],
}
```

补充：Layer 2 原始候选阶段，`transform_id` / `constraint_id` 使用 pair 级格式 `"{alignment_id}:..."` 保留 provenance；跨 train 聚合后的下游候选池允许重发为 family 级格式 `"{alignment_family_id}:..."`，但 `alignment_id` 与 `alignment_family_id` 两个显式字段都必须保留。

补充：`alignment_family_id` 只定义候选池边界，不等于所有 constraint 都要被 family 内全部 program 共享。尤其 `size_rule:*` 必须在组装具体 hypothesis 时，按 program 的 `applicable_pairs` 重新投影和绑定。

### 3.4 Layer 3 假设输出

```text
Hypothesis = {
  plan_id: str,
  alignment_id: str,                         -- 代表性原始对齐 ID，用于 provenance / 归因
  alignment_family_id: str,                  -- family 级绑定键，用于筛选与执行
  constraint_subset: {
    strong: [str],
    weak: [str],
  },
  program: str,
}
```

Step 1 约束：允许 `weak` 为空列表；不得省略 `alignment_id` 与 `alignment_family_id`。

补充：同一 `program` 文本若在其相关 pair 上对应多个 `size_rule:*`，允许生成多个 `Hypothesis` 版本；它们只在 `constraint_subset` 上不同，但都仍属于合法 Step 1 输出。

### 3.5 Layer 5 最小归因输出

以下为 Step 1 强制落盘的最小归因子集。主架构完整 schema 中的 `failure_confidence`、`system_state_version`、`expansion_hint` 等字段在 Step 1 不要求落盘；若实现上保留，占位为 null 或空结构即可。

```text
Attribution = {
  task_id: str,
  eval_mode: "A",
  success: bool,
  pixel_accuracy: float,
  failure_type: "NONE" | "PERCEPTION_FAIL" | "SELECTION_FAIL" | "ABSTRACTION_FAIL" | "EXECUTION_FAIL",
  failure_detail: str | null,
  selected_plan: str,
  selected_alignment: str,
  selected_alignment_family: str,
  selected_program: str,
  selected_constraints: {
    strong: [str],
    weak: [str],
  },
  search_stats: SearchStats,
}

SearchStats = {
  candidates_generated: int,
  candidates_evaluated: int,
  search_time_ms: int,
  beam_saturated: bool,
  layer1_time_ms: int,
  layer2_time_ms: int,
  layer3_time_ms: int,
  layer4_time_ms: int,
  layer5_time_ms: int,
}
```

Step 1 中 `eval_mode` 固定为 `A`，因为所有任务都可访问真值。

## 4. Step 1 对齐白名单

Step 1 只允许一对一对象对齐，并只允许以下三种方法：

| 方法 | 是否启用 | 说明 |
| --- | --- | --- |
| 像素重合匹配 | 是 | 适用于对象位置未变或轻微扰动 |
| 颜色+形状匹配 | 是 | 适用于发生平移但形状保持不变 |
| 最优二部匹配 | 是 | 在一对一前提下做全局最小代价匹配 |
| 合并检测 | 否 | 推迟到 Step 3 |
| 拆分检测 | 否 | 推迟到 Step 3 |

对齐失败回退规则固定为：

1. 对某个 `plan_id`，依次尝试白名单中的一对一对齐方法。
2. 若该 `plan_id` 下全部对齐方法都失败，则丢弃该分割方案。
3. 若全部分割方案都失败，则任务级失败归因为 `PERCEPTION_FAIL`。
4. Step 1 不允许保留“不确定对齐”继续候选生成。

## 5. Step 1 最小约束与输出尺寸推断

本节定义的是 Step 1 针对 Copy / Center 任务族的最小约束子集，不改写主架构中的完整候选约束表。

### 5.1 允许的约束类型

| 约束类型 | Step 1 是否实现 | 说明 |
| --- | --- | --- |
| 输出尺寸约束 | 是 | 仅支持有限四类尺寸规则 |
| 颜色映射一致性 | 是 | 仅支持恒等映射或固定颜色替换 |
| 相对位置约束 | 是 | 仅用于 Copy / Center 中的基础位置检查 |
| 局部一致性 | 否 | 推迟到 Step 2 |
| 计数守恒 | 否 | 推迟到 Step 2 |
| 全局单调性 | 否 | 推迟到 Step 2 |

### 5.2 输出尺寸推断范围

Step 1 只支持以下四种输出尺寸规则：

1. `preserve_input_size`：所有 train pair 的 input 与 output 尺寸相同。
2. `fit_transformed_extent`：输出尺寸取执行后所有对象像素并集的最小外接矩形，适用于 Copy1 / Copy5 / Copy6 这类由 copy + translate 导致的画布扩张。
3. `crop_selected_bbox`：输出尺寸取被选中中心对象的 bbox，适用于 Center3 一类中心对象抽取任务。
4. `crop_center_cell`：输出尺寸固定为 `1x1`，取中心单元的值，适用于 Center2 一类中心单元抽取任务。

补充：Center1 一类“保留原画布，仅在中心位置补一个像素”的任务不需要新增输出尺寸规则；它应落在 `preserve_input_size + fill(mode=center_cell)` 这一现有组合里解决。

补充：Center3 一类任务允许在 Step 1 中通过 `center_object` 选择器表达“先选中心对象，再 `crop` 或 `delete`”；Center4 一类任务除 `center_object` 外，还允许用 `delete(mode=input_center_component)` 表达“删除输入中心处的同色连通域”，因为该连通域未必在当前分割 plan 中成为独立对象。Copy2 / Center5 / Center6 一类任务允许在 Step 1 中通过 `smallest_object` 或 `rare_color_object` 作为源对象选择器，并结合 `to_input_center_*` 或 `to_largest_object_center_*` 表达一次性中心放置或搬运；若当前 plan 无法把稀有色源图样与目标锚点稳定暴露成单对象，还允许使用固定语义的 `translate(mode=rare_color_motif_to_largest_component_center)` 完成同一类单次中心搬运。

Step 1 不支持更一般的固定尺寸模板、比例缩放、tile、construct_grid 或依赖复杂布局规则的输出尺寸推断。

说明：Step 1 的输出尺寸推断已经放宽到足以覆盖 Copy1-6 与 Center1-6，但仍是针对这两个概念组的最小子集，不改写主架构中的完整输出尺寸推断表。

### 5.3 强弱约束约定

Step 1 保留 `strong/weak` 结构，但采用保守策略：

1. 只有在所有 train pair 上都成立的约束，才进入 `strong`。
2. `weak` 在 Step 1 中允许为空，不要求通过弱约束做 tie-break。
3. Step 1 不因“弱约束定义不充分”而阻塞实现。

## 6. Step 1 运行遥测字段表

Step 1 采用标准版遥测，每个任务至少记录以下字段：

| 字段 | 含义 |
| --- | --- |
| task_id | 当前任务 ID |
| selected_plan | 最终选中的分割方案 |
| selected_alignment | 最终选中的代表性原始对齐 ID |
| selected_alignment_family | 最终选中的 family 级对齐键 |
| selected_program | 最终选中的程序文本 |
| candidates_generated | 候选总数 |
| candidates_evaluated | 进入 Step 1 最小 beam 后实际执行评估的 hypothesis 数 |
| beam_saturated | hypothesis 预排序后是否因 `STEP1_BEAM_SIZE` 截断而丢弃候选 |
| layer1_time_ms | Layer 1 耗时 |
| layer2_time_ms | Layer 2 耗时 |
| layer3_time_ms | Layer 3 耗时 |
| layer4_time_ms | Layer 4 耗时 |
| layer5_time_ms | Layer 5 耗时 |
| search_time_ms | 任务总搜索时间 |
| success | 是否精确求解 |
| pixel_accuracy | 像素级精度 |
| failure_type | 失败归因标签 |

Step 1 当前 beam 是最小实现：先按字符串级 `pre_priority` proxy 对 hypothesis 预排序，再取前 `STEP1_BEAM_SIZE = 32` 个进入执行评估。Step 1 不要求记录完整 Top-K 快照、完整候选程序列表或扩展建议。

由于 Step 1 不启用排序模型，主架构 `search_stats` 中与概念组权重相关的字段在本阶段不要求记录。

## 7. Step 1 明确不做的能力

为防止实现越界，以下能力在 Step 1 中一律视为禁用：

1. 排序模型训练与推理。
2. 知识状态写回、扩展准入、三阶段知识重写。
3. merge / split / partition。
4. bbox / bg_fg / repeat / nested 分割策略。
5. 完整关系集与完整约束集。
6. 路径 B 约束求解。
7. 诊断任务消费。
8. 为提高成功率而加入样例级 ad-hoc 特判。
9. 未经文档显式登记、却以“通用能力”名义混入 Step 1 的任务族级受限 mode。

## 8. 与后续 Step 的接口约定

Step 1 虽然收缩，但以下接口必须与后续 Step 保持兼容：

1. `alignment_id` 与 `alignment_family_id` 都不得省略。
2. `Hypothesis` 必须维持 `(plan_id, alignment_id, alignment_family_id, constraint_subset, program)` 结构。
3. `Attribution` 必须保留 `selected_plan`、`selected_alignment`、`selected_alignment_family`、`selected_program`、`selected_constraints` 与 `search_stats`；其余完整 schema 字段在 Step 1 可省略，但字段语义不得改写。
4. `ProgramSketch` 与 `Program` 的分层必须保留，即使 Step 1 只实现 Program 的严格子集。
5. `strong/weak` 约束结构必须保留，即使 Step 1 的 `weak` 为空。

## 9. 使用说明

后续编写 Step 1 实现设计文档时：

1. 先引用本附录，不再重复争论任务范围与接口边界。
2. 正文只写实现顺序、模块职责、验证门槛与测试策略。
3. 若正文与本附录冲突，以本附录为准。
