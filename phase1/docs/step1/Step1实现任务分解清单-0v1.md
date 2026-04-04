# 第一阶段 Step 1 实现任务分解清单

> 版本：v0.1
>
> 状态：已实施冻结
>
> 作用：把 [Step1实现设计-0v1.md](phase1/docs/step1/Step1实现设计-0v1.md) 和 [Step1最小接口与任务清单附录-0v1.md](phase1/docs/step1/Step1最小接口与任务清单附录-0v1.md) 压缩成可直接编码的任务清单，供 codex 按顺序落地。

## 1. 使用方式

本清单只服务于 Step 1 编码落地，不再讨论架构方向。

Step 1 的尺寸与原语边界已经按 Copy1-6 和 Center1-6 重写。本清单以下内容默认以“允许有限画布扩张、允许中心裁剪、允许 fill 与 crop 的受限版本”为前提。

执行规则固定如下：

1. 若本清单与 [Step1最小接口与任务清单附录-0v1.md](phase1/docs/step1/Step1最小接口与任务清单附录-0v1.md) 冲突，以附录为准。
2. 若本清单与 [Step1实现设计-0v1.md](phase1/docs/step1/Step1实现设计-0v1.md) 冲突，以附录优先、正文次之，本清单必须回改，不允许在代码里自行解释。
3. 若编码过程中发现某任务需要 Step 2 能力，必须停止并标记为越界，不允许“先写进去再说”。

## 2. 硬边界

编码过程中必须始终满足以下硬边界：

1. 只允许使用 Copy1-6 与 Center1-6 作为 Step 1 训练任务。
2. Copy7-10 与 Center7-10 在 Step 1-2 全程不可见，不允许用于调试、人工验证或参数选择。
3. 只允许 cc4、cc8、whole_grid 三种分割方案。
4. 只允许一对一对象对齐。
5. 只允许 copy、translate、rotate、flip、delete、recolor、fill、crop 八种原语进入候选与执行。
6. 不允许 ForEach、If、group_by、merge、partition、construct_grid、路径 B。
7. 不允许排序模型训练、不允许知识写回、不允许扩展准入、不允许知识重写。
8. `Hypothesis` 必须显式区分 `alignment_id` 与 `alignment_family_id`，不允许再把 family 级语义塞进 `alignment_id`。
9. `Attribution` 必须保留 `selected_plan`、`selected_alignment`、`selected_alignment_family`、`selected_program`、`selected_constraints`、`search_stats`。
10. `strong/weak` 结构必须保留，即使 Step 1 的 `weak` 为空。
11. 输出尺寸只允许四类规则：`preserve_input_size`、`fit_transformed_extent`、`crop_selected_bbox`、`crop_center_cell`。

## 3. 目录落地目标

编码完成后，目录应至少包含以下结构：

```text
phase1/
├── src/
│   └── step1/
│       ├── __init__.py
│       ├── config.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── models.py
│       ├── layer1/
│       │   ├── __init__.py
│       │   ├── perception.py
│       │   ├── objects.py
│       │   └── relations.py
│       ├── layer2/
│       │   ├── __init__.py
│       │   ├── alignment.py
│       │   ├── diff.py
│       │   ├── constraints.py
│       │   └── sketches.py
│       ├── layer3/
│       │   ├── __init__.py
│       │   ├── hypothesis.py
│       │   ├── scoring.py
│       │   └── selector.py
│       ├── layer4/
│       │   ├── __init__.py
│       │   ├── dsl.py
│       │   ├── executor.py
│       │   └── render.py
│       ├── layer5/
│       │   ├── __init__.py
│       │   ├── verify.py
│       │   └── attribution.py
│       ├── runner/
│       │   ├── __init__.py
│       │   ├── task_runner.py
│       │   └── batch_runner.py
│       └── utils/
│           ├── __init__.py
│           ├── debug_dump.py
│           ├── ids.py
│           └── timing.py
├── tests/
│   └── step1/
│       ├── __init__.py
│       ├── fixtures.py
│       ├── test_loader.py
│       ├── test_layer1.py
│       ├── test_layer2.py
│       ├── test_layer3.py
│       ├── test_layer4.py
│       ├── test_layer5.py
│       └── test_runner.py
└── outputs/
    └── step1/
        ├── debug/
        └── reports/
```

测试目录必须一开始就建立，不允许“先写代码，最后再补测试”。

## 4. 全局编码约定

### 4.1 语言与依赖

1. 使用 Python 标准库实现，不引入第三方依赖。
2. 数据结构优先使用 `dataclasses`、`typing`、`pathlib`、`json`。
3. 测试框架使用标准库 `unittest`。
4. 不使用 notebook，不使用隐藏缓存，不使用随机性。

### 4.2 稳定 ID 规则

以下 ID 格式必须固定，避免调试产物在不同运行间漂移：

```text
plan_id         = method                       # "cc4" | "cc8" | "whole_grid"
alignment_id    = "{plan_id}:{method}:{pair_index}"      # 单个 train pair 上的原始对齐 ID
alignment_family_id = "{plan_id}:{method}"               # 跨全部 train pair 聚合后的对齐家族 ID
pair_transform_id    = "{alignment_id}:transform:{local_index}"
pair_constraint_id   = "{alignment_id}:constraint:{local_index}"
family_transform_id  = "{alignment_family_id}:transform:{local_index}"
family_constraint_id = "{alignment_family_id}:constraint:{local_index}"
```

补充约定：

1. `align_objects(...)` 直接产出的 `Alignment.alignment_id` 使用原始 `alignment_id`。
2. `Alignment.alignment_family_id` 与 `alignment_id` 同时存在，显式表达 raw/family 两层语义。
3. Layer 2 原始 `CandidateTransform` / `CandidateConstraint` 必须分别使用 `pair_transform_id` / `pair_constraint_id`，保留 pair 级 provenance。
4. 从跨 train 聚合开始，下游候选池中的运行时 ID 改用 `family_transform_id` / `family_constraint_id`，而显式字段 `alignment_id` 继续保留原始 provenance，不允许再借用 `alignment_id` 承载 family 级语义。

### 4.3 运行命令

默认测试命令固定为：

```bash
python -m unittest discover -s phase1/tests/step1 -p "test_*.py"
```

默认批量运行命令固定为：

```bash
python -m phase1.src.step1.runner.batch_runner
```

若实际包导入路径需要调整，只允许调整命令与包初始化，不允许改动模块职责边界。

## 5. 源码公共接口

本节只定义必须存在的公共接口。内部 helper 可增删，但不得替代以下接口。

### 5.1 data/models.py

必须定义以下类型：

```python
Grid = list[list[int]]
Cell = tuple[int, int]
RelationEdge = tuple[str, str, str]

@dataclass(frozen=True)
class ExamplePair:
    pair_index: int
    split: str          # "train" | "test"
    input: Grid
    output: Grid | None

@dataclass(frozen=True)
class ArcTask:
    task_id: str
    concept: str
    file_path: str
    train_pairs: list[ExamplePair]
    test_pairs: list[ExamplePair]

@dataclass(frozen=True)
class ObjectData:
    id: str
    pixels: set[Cell]
    bbox: tuple[int, int, int, int]
    attrs: dict[str, int | float]

@dataclass(frozen=True)
class SegmentationPlan:
    plan_id: str
    method: str
    objects: list[ObjectData]
    relations: list[RelationEdge]

@dataclass(frozen=True)
class PerceptionOutput:
    segmentation_plans: list[SegmentationPlan]

@dataclass(frozen=True)
class Alignment:
    alignment_id: str
    alignment_family_id: str
    matched_pairs: list[tuple[str, str, float]]
    unmatched_input: list[str]
    unmatched_output: list[str]
    merge_groups: list[list[str]]
    split_groups: list[list[str]]

@dataclass(frozen=True)
class CandidateTransform:
    transform_id: str
    alignment_id: str
    alignment_family_id: str
    program: object
    applicable_pairs: list[int]
    match_score: float

@dataclass(frozen=True)
class CandidateConstraint:
    constraint_id: str
    alignment_id: str
    alignment_family_id: str
    predicate: str
    holds_in: list[int]

`CandidateConstraint.predicate` 在 Step 1 中必须使用稳定字符串编码，至少覆盖：

1. `size_rule:preserve_input_size`
2. `size_rule:fit_transformed_extent`
3. `size_rule:crop_selected_bbox`
4. `size_rule:crop_center_cell`
5. `color_map:<src_color>-><dst_color>`
6. `relative_position:<relation_name>`

@dataclass(frozen=True)
class CandidateSet:
    plan_id: str
    candidate_alignments: list[Alignment]
    candidate_transforms: list[CandidateTransform]
    candidate_constraints: list[CandidateConstraint]

@dataclass(frozen=True)
class Hypothesis:
    plan_id: str
    alignment_id: str
    alignment_family_id: str
    constraint_subset: dict[str, list[str]]
    program: str

@dataclass(frozen=True)
class SearchStats:
    candidates_generated: int
    candidates_evaluated: int
    search_time_ms: int
    beam_saturated: bool
    layer1_time_ms: int
    layer2_time_ms: int
    layer3_time_ms: int
    layer4_time_ms: int
    layer5_time_ms: int

@dataclass(frozen=True)
class Attribution:
    task_id: str
    eval_mode: str
    success: bool
    pixel_accuracy: float
    failure_type: str
    failure_detail: str | None
    selected_plan: str
    selected_alignment: str
    selected_alignment_family: str
    selected_program: str
    selected_constraints: dict[str, list[str]]
    search_stats: SearchStats
```

要求：

1. `merge_groups` 与 `split_groups` 在 Step 1 运行时必须恒为空列表。
2. `constraint_subset` 与 `selected_constraints` 必须始终保留 `strong` 和 `weak` 两个 key。
3. 所有 dataclass 必须可 JSON 序列化或可被显式转换为 JSON 结构。

### 5.2 config.py

必须导出：

```python
STEP1_TRAIN_TASKS: list[tuple[str, str, str]]
STEP1_DIAGNOSTIC_TASKS: list[tuple[str, str, str]]
ALLOWED_SEGMENTATION_METHODS: tuple[str, ...]
ALLOWED_PRIMITIVES: tuple[str, ...]
ALLOWED_OUTPUT_SIZE_RULES: tuple[str, ...]
ALLOWED_FAILURE_TYPES: tuple[str, ...]
STEP1_BEAM_SIZE: int
DEFAULT_OUTPUT_DIR: str
```

要求：

1. `STEP1_TRAIN_TASKS` 必须精确覆盖 Copy1-6 与 Center1-6。
2. `STEP1_DIAGNOSTIC_TASKS` 必须精确覆盖 Copy7-10 与 Center7-10。
3. runner 默认只读取 `STEP1_TRAIN_TASKS`。

### 5.3 data/loader.py

必须导出：

```python
def load_task(concept: str, task_id: str, file_path: str) -> ArcTask: ...
def load_step1_train_tasks() -> list[ArcTask]: ...
def load_step1_task_ids() -> list[str]: ...
```

要求：

1. 不提供默认批量加载诊断任务的入口函数。
2. JSON 解析失败时抛出带文件路径的异常。
3. `ExamplePair.split` 在 train/test 上必须显式标记。

### 5.4 utils/ids.py

必须导出：

```python
def make_plan_id(method: str) -> str: ...
def make_alignment_id(plan_id: str, method: str, pair_index: int) -> str: ...
def make_alignment_family_id(plan_id: str, method: str) -> str: ...
def make_pair_transform_id(alignment_id: str, local_index: int) -> str: ...
def make_family_transform_id(alignment_family_id: str, local_index: int) -> str: ...
def make_pair_constraint_id(alignment_id: str, local_index: int) -> str: ...
def make_family_constraint_id(alignment_family_id: str, local_index: int) -> str: ...
```

### 5.5 utils/timing.py

必须导出：

```python
@contextmanager
def timed_section(metrics: dict[str, int], key: str): ...
```

要求：

1. 所有 layer 耗时通过同一机制记录。
2. 时间单位统一为毫秒。

### 5.6 utils/debug_dump.py

必须导出：

```python
def dump_json(path: str | Path, payload: dict | list) -> None: ...
def dump_task_debug_bundle(task_id: str, output_dir: str | Path, bundle: dict) -> None: ...
```

要求：

1. `bundle` 至少支持写出 `layer1.json`、`layer2.json`、`selected_hypothesis.json`、`attribution.json`。
2. 输出目录不存在时自动创建。

### 5.7 layer4/dsl.py

必须定义 Step 1 内部 AST，并导出：

```python
@dataclass(frozen=True)
class PrimitiveCall: ...

@dataclass(frozen=True)
class CopyClause: ...

@dataclass(frozen=True)
class CopyBlock: ...

@dataclass(frozen=True)
class Step1Program: ...

def render_program(program: Step1Program) -> str: ...
def validate_step1_program(program: Step1Program) -> None: ...
```

要求：

1. AST 只能表达附录允许的 Step 1 DSL 子集。
2. `validate_step1_program` 遇到 `ForEach`、`If`、`group_by`、`merge`、`partition`、`construct_grid` 语义时必须报错。
3. `copy` 必须通过 `on_copy` / `on_original` 子句表达，不允许裸 `copy`。

### 5.8 layer4/render.py

必须导出：

```python
def render_objects(
    objects: list[ObjectData],
    background_color: int,
    grid_shape: tuple[int, int],
    program_order: list[str] | None = None,
) -> Grid: ...

def infer_output_grid_shape(
    input_grid: Grid,
    objects: list[ObjectData],
    size_rule: str,
    crop_bbox: tuple[int, int, int, int] | None = None,
) -> tuple[int, int]: ...
```

要求：

1. 背景色先填充。
2. 默认覆盖顺序按面积从大到小。
3. 同面积冲突按 `program_order` 的后写覆盖前写。
4. `infer_output_grid_shape` 只允许实现四类输出尺寸规则。
5. 仅在 `preserve_input_size` 模式下允许越界截断。

### 5.9 layer4/executor.py

必须导出：

```python
def execute_program(
    program: Step1Program,
    input_plan: SegmentationPlan,
    input_grid: Grid,
    output_size_rule: str,
) -> Grid: ...
```

要求：

1. 只实现 copy、translate、rotate、flip、delete、recolor、fill、crop。
2. 执行前必须调用 `validate_step1_program`。
3. `output_size_rule` 只允许 `preserve_input_size`、`fit_transformed_extent`、`crop_selected_bbox`、`crop_center_cell` 四类规则。
4. `execute_program` 不自行猜测输出尺寸规则，只消费调用方显式传入的 `output_size_rule`。
5. `translate` 的 `dx/dy` 除整数常量外，还必须支持有限符号参数：`input_width`、`input_height`、`object_width`、`object_height`、`to_input_center_dx`、`to_input_center_dy`、`to_largest_object_center_dx`、`to_largest_object_center_dy` 及其带符号版本；解析后按当前对象、当前输入网格与当前 plan 即时求值。
6. `target` 除 `all` 与显式对象 ID 外，还必须支持 `center_object`、`smallest_object`、`rare_color_object` 三个受限选择器。
7. 当 `output_size_rule == crop_selected_bbox` 时，若程序中存在 `crop(..., mode=tight_bbox)` 产生的对象，执行结果必须只保留被裁剪对象，而不是连同未裁剪对象一并渲染。
8. `delete(..., mode=input_center_component)` 必须删除输入画布中心单元所在的 4 邻域同色连通域；若该连通域位于当前 plan 的单个大对象内部，也必须只删除该子区域，而不是整对象。

### 5.10 layer1/objects.py

必须导出：

```python
def extract_cc_objects(grid: Grid, connectivity: int) -> list[set[Cell]]: ...
def build_object(object_id: str, pixels: set[Cell], grid: Grid) -> ObjectData: ...
def build_whole_grid_object(grid: Grid) -> ObjectData: ...
```

要求：

1. `connectivity` 只允许 4 或 8。
2. `build_object` 必须填充 `dominant_color`、`area`、`height`、`width`、`center_row`、`center_col`。
3. 对象 ID 在同一 plan 内必须稳定，可按 bbox 再按像素字典序排序生成。

### 5.11 layer1/relations.py

必须导出：

```python
def extract_relations(objects: list[ObjectData]) -> list[RelationEdge]: ...
```

要求：

1. 只产出 `relative_position` 与 `alignment` 相关 relation。
2. 不产出颜色映射、尺寸映射、邻接、包含、对称。

### 5.12 layer1/perception.py

必须导出：

```python
def build_segmentation_plan(grid: Grid, method: str) -> SegmentationPlan: ...
def perceive_grid(grid: Grid) -> PerceptionOutput: ...
```

要求：

1. `perceive_grid` 必须固定输出 `cc4`、`cc8`、`whole_grid` 三个 plan。
2. `plan_id` 必须直接等于 method。

### 5.13 layer2/alignment.py

必须导出：

```python
def align_objects(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    pair_index: int,
) -> list[Alignment]: ...
```

要求：

1. 按顺序尝试像素重合匹配、颜色+形状匹配、最优二部匹配。
2. 仅返回一对一 Alignment。
3. 三种方法都失败时返回空列表。
4. 不允许返回“不确定对齐”。

说明：最优二部匹配使用标准库实现的精确最小代价分配。若对象数较小，允许用位压 DP；不引入第三方库。

### 5.14 layer2/diff.py

必须导出：

```python
def classify_object_diff(input_obj: ObjectData, output_obj: ObjectData) -> str: ...
def classify_alignment_diffs(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    alignment: Alignment,
) -> list[str]: ...
```

要求：

1. 差异类型只允许 `copy`、`fill`、`delete`、`translate`、`rotate_or_flip`、`recolor`、`crop`。
2. 不产出 merge、split、scale、tile、construct_grid。

### 5.15 layer2/constraints.py

必须导出：

```python
def extract_constraints(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    alignment: Alignment,
    pair_index: int,
) -> list[CandidateConstraint]: ...

def partition_constraints(
    constraints: list[CandidateConstraint],
    train_pair_count: int,
) -> dict[str, list[str]]: ...
```

要求：

1. 只实现输出尺寸约束、颜色映射一致性、相对位置约束。
2. `partition_constraints` 必须始终返回 `strong` 和 `weak`。
3. Step 1 允许 `weak` 为空。
4. 输出尺寸约束只允许四类规则：`preserve_input_size`、`fit_transformed_extent`、`crop_selected_bbox`、`crop_center_cell`。
5. 每个最终进入 `Hypothesis.constraint_subset["strong"]` 的输出尺寸约束都必须使用 `size_rule:*` 编码，且强约束中必须恰好存在一个 `size_rule:*`。

### 5.16 layer2/sketches.py

必须导出：

```python
def generate_candidate_transforms(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    alignment: Alignment,
    pair_index: int,
) -> list[CandidateTransform]: ...

def build_candidate_set(
    plan_id: str,
    alignments: list[Alignment],
    transforms: list[CandidateTransform],
    constraints: list[CandidateConstraint],
) -> CandidateSet: ...
```

要求：

1. `program` 只能是 Step 1 ProgramSketch AST。
2. 只允许单步原语或两步序列复合。
3. 允许 `copy ; on_copy:` / `copy ; on_original:`。
4. 不允许控制流。
5. 对 Copy 类差异，必须显式尝试 `copy ; on_copy: translate(...)` 型候选；位移参数可来自已观测 dx/dy，也可来自有限符号表 `input_width`、`input_height`、`object_width`、`object_height` 及其带符号版本，但不得引入循环或一般模板展开。
6. 对 Center 类差异，必须显式尝试 `fill[target=..., mode=center_cell]` 型候选；这属于受限 `fill`，不得通过新增原语绕开。
7. 当观测位移可被上述有限符号表解释时，必须同时产出符号参数版本，避免因 pair 级常量不同而阻断跨 pair 聚合。
8. 对中心对象抽取 / 删除类任务，必须显式尝试 `crop[target=center_object,mode=tight_bbox]` 与 `delete[target=center_object]` 这类 selector 版本。
9. 对单源对象中心放置 / 搬运类任务，必须显式尝试以 `smallest_object` 或 `rare_color_object` 为源对象选择器，并结合 `to_input_center_*` 或 `to_largest_object_center_*` 的受限参数版本。
10. 对“输入中心处的同色连通域需要被删除，但未必形成独立对象”的任务，必须显式尝试 `delete[target=all,mode=input_center_component]`；该 mode 固定表示删除输入画布中心单元所在的 4 邻域同色连通域，不新增 primitive。
11. 对“全局稀有色图样需要整体搬到中心锚点，但当前 plan 可能把源图样并进多色对象或把锚点切碎”的任务，必须显式尝试 `translate[target=all,mode=rare_color_motif_to_largest_component_center]`；该 mode 固定表示把全局最稀有非零颜色的全部像素图样平移到最大 8 邻域非零连通块中心，不新增 primitive。

### 5.17 layer3/hypothesis.py

必须导出：

```python
def assemble_hypotheses(candidate_sets: list[CandidateSet]) -> list[Hypothesis]: ...
```

要求：

1. 禁止跨 `alignment_id` 混搭程序和约束。
2. `program` 必须序列化为稳定 DSL 文本。
3. `size_rule:*` 的强约束绑定粒度不得粗于 program。组装 hypothesis 时，必须先把候选约束投影到该 program 的 `applicable_pairs`，再决定其唯一强 `size_rule:*`。
4. 若同一 program 在其相关 pair 上同时观察到多个 `size_rule:*`，必须拆成多个 hypothesis，而不是按 family 级多数票只保留一个。

### 5.18 layer3/scoring.py

必须导出：

```python
def description_length(hypothesis: Hypothesis) -> int: ...
def pre_priority(hypothesis: Hypothesis) -> tuple[float, int]: ...
def mismatch_sum(outputs: list[Grid], targets: list[Grid]) -> int: ...
```

要求：

1. `pre_priority` 只使用字符串级代理 `attr_ref_ratio` 与 `ast_depth`，不得把当前实现写成 AST / AttrRef 精确分析。
2. `description_length` 只对 program、强约束、常量数计费。

### 5.19 layer3/selector.py

必须导出：

```python
def apply_hypothesis_beam(
    hypotheses: list[Hypothesis],
    beam_size: int = STEP1_BEAM_SIZE,
) -> tuple[list[Hypothesis], bool]: ...

def group_equivalent_hypotheses(
    hypotheses: list[Hypothesis],
    rendered_train_outputs: dict[str, list[Grid]],
) -> dict[str, list[Hypothesis]]: ...

def select_best_hypothesis(
    hypotheses: list[Hypothesis],
    train_inputs: list[Grid],
    train_outputs: list[Grid],
) -> tuple[Hypothesis, dict]: ...
```

要求：

1. 在执行评估前，必须先按当前 `pre_priority` 对 hypothesis 预排序，并截到 `STEP1_BEAM_SIZE`。
2. `candidates_evaluated` 必须等于进入该最小 beam 后的 hypothesis 数；若发生截断，`beam_saturated = true`。
3. 等价类按 train 输出向量哈希分组。
4. 每组保留描述长度最短的代表元参与主评估。
5. 等价类成员不得删除。
6. Step 1 不实现完整 test tie-break，但必须把成员列表、类大小、代表元约束集记录到 selector 的调试结果中。
7. 当不存在 train 精确匹配时，允许在 `mismatch_sum + lambda * L(h)` 之上加入极小、固定、显式记录的回退罚分，但该罚分只允许用于压制明显退化候选，不得替代主排序。
8. 当前唯一允许的回退罚分对象，是语义空转的 `copy` 块，例如 `copy ; on_copy: ; on_original:`；罚分来源与数值必须写入 selector 调试结果。

### 5.20 layer5/verify.py

必须导出：

```python
def pixel_accuracy(predicted: Grid, target: Grid) -> float: ...
def verify_constraints(predicted: Grid, hypothesis: Hypothesis) -> tuple[list[str], list[str]]: ...
def classify_failure(
    has_perception: bool,
    has_hypothesis: bool,
    execution_ok: bool,
    exact_match: bool,
) -> str: ...
```

### 5.21 layer5/attribution.py

必须导出：

```python
def build_attribution(
    task_id: str,
    hypothesis: Hypothesis | None,
    success: bool,
    pixel_acc: float,
    failure_type: str,
    failure_detail: str | None,
    search_stats: SearchStats,
) -> Attribution: ...
```

要求：

1. `eval_mode` 固定为 `A`。
2. 必须写出 `selected_constraints`。
3. 不实现 `failure_confidence`、`system_state_version`、`expansion_hint`。

### 5.22 runner/task_runner.py

必须导出：

```python
def run_task(task: ArcTask, output_dir: str | Path) -> Attribution: ...
```

要求：

1. 严格按 Step 1 正文中的 7 步主流程执行。
2. 必须写出调试产物。
3. 不能访问诊断任务。
4. 在调用 `execute_program(...)` 前，必须先从 `hypothesis.constraint_subset["strong"]` 中解析出唯一的 `size_rule:*`，若不是恰好一个则直接判为假设无效并进入失败归因。

### 5.23 runner/batch_runner.py

必须导出：

```python
def run_step1_batch(output_dir: str | Path) -> list[Attribution]: ...
def build_summary(attributions: list[Attribution]) -> dict: ...
```

要求：

1. 默认只跑 `STEP1_TRAIN_TASKS`。
2. `summary` 至少包含精确求解数、失败类型分布、每层平均耗时、最常选中的分割方案与对齐策略。

## 6. 编码顺序

禁止全量并行乱写。编码顺序必须固定如下。

### Phase 0：骨架与类型

目标：先把可导入的包、稳定 schema、任务清单和测试框架建好。

文件：

1. `src/step1/__init__.py`
2. `src/step1/config.py`
3. `src/step1/data/models.py`
4. `src/step1/data/loader.py`
5. `src/step1/utils/ids.py`
6. `src/step1/utils/timing.py`
7. `src/step1/utils/debug_dump.py`
8. `tests/step1/__init__.py`
9. `tests/step1/fixtures.py`
10. `tests/step1/test_loader.py`

退出门槛：

1. `python -m unittest discover -s phase1/tests/step1 -p "test_*.py"` 至少能跑通 loader 和 model 测试。
2. `load_step1_train_tasks()` 返回 12 个任务。
3. 默认代码路径无法批量加载诊断任务。

### Phase 1：先做执行器，不做搜索

目标：先把 Layer 4 做成可单独验证的确定性解释器。

文件：

1. `src/step1/layer4/dsl.py`
2. `src/step1/layer4/render.py`
3. `src/step1/layer4/executor.py`
4. `tests/step1/test_layer4.py`

退出门槛：

1. 八个原语各有独立单测。
2. `copy` 焦点语义正确。
3. 渲染规则正确：背景填充、面积优先覆盖、有限尺寸扩张、中心裁剪、空区域保留背景色。

### Phase 2：再做感知层

目标：保证三种分割方案和最小属性稳定输出。

文件：

1. `src/step1/layer1/objects.py`
2. `src/step1/layer1/relations.py`
3. `src/step1/layer1/perception.py`
4. `tests/step1/test_layer1.py`

退出门槛：

1. 同一输入多次运行对象 ID 稳定。
2. cc4 与 cc8 在对角接触样例上结果不同。
3. whole_grid 始终只产出一个对象。

### Phase 3：做候选生成层

目标：从输入输出 plan 中产出可追溯到原始 `alignment_id` 的候选。

说明：这里的“可追溯到 `alignment_id`”指 pair 级原始对齐；进入跨 train 聚合后，下游候选与假设统一绑定 `alignment_family_id`。

文件：

1. `src/step1/layer2/alignment.py`
2. `src/step1/layer2/diff.py`
3. `src/step1/layer2/constraints.py`
4. `src/step1/layer2/sketches.py`
5. `tests/step1/test_layer2.py`

退出门槛：

1. 对齐按固定顺序尝试三种一对一方法。
2. 全失败时返回空列表，不返回“不确定对齐”。
3. 每个原始 CandidateTransform 和 CandidateConstraint 都同时保留 pair 级 `alignment_id` 与 family 级 `alignment_family_id`。

### Phase 4：做筛选层

目标：把 CandidateSet 收成可执行 Hypothesis。

文件：

1. `src/step1/layer3/hypothesis.py`
2. `src/step1/layer3/scoring.py`
3. `src/step1/layer3/selector.py`
4. `tests/step1/test_layer3.py`

退出门槛：

1. 不发生跨 `alignment_family_id` 混搭，且 `alignment_id` 只用于 raw provenance，不再承担 family 级绑定语义。
2. 等价类归并保留成员，不做语义删除。
3. 能输出 `selected_plan`、`selected_alignment`、`selected_program`、`selected_constraints`。
4. 不出现 family 级 `size_rule:*` 覆盖 program 级语义的情况；同一 program 若存在多个合法 size-rule 版本，缓存键与调试输出必须能区分这些版本。

### Phase 5：做验证与归因层

目标：给每个任务产出结构化 Attribution。

文件：

1. `src/step1/layer5/verify.py`
2. `src/step1/layer5/attribution.py`
3. `tests/step1/test_layer5.py`

退出门槛：

1. 成功样例输出 `NONE`。
2. 失败样例至少能区分 `PERCEPTION_FAIL`、`SELECTION_FAIL`、`ABSTRACTION_FAIL`、`EXECUTION_FAIL`。
3. `Attribution` 包含 `selected_constraints` 与 `search_stats`。

### Phase 6：做 runner 与批量报告

目标：跑通 Step 1 端到端闭环并落盘结果。

文件：

1. `src/step1/runner/task_runner.py`
2. `src/step1/runner/batch_runner.py`
3. `tests/step1/test_runner.py`

退出门槛：

1. 单任务运行会写出 4 个基础调试文件。
2. 批量运行只消费 12 个训练任务。
3. `summary.json` 与 `summary.md` 可生成。

## 7. 首批测试样例

首批测试样例分为三层：合成单元样例、固定 smoke 样例、首批回归任务。

### 7.1 合成单元样例

`tests/step1/fixtures.py` 必须至少定义以下 fixture：

1. `diag_touch_grid`：验证 cc4 与 cc8 在对角接触时的分割差异。
2. `single_object_translate_right`：验证 translate。
3. `copy_then_translate_by_width`：验证 `copy ; on_copy: translate(...)`。
4. `single_object_recolor`：验证 recolor。
5. `single_object_delete`：验证 delete。
6. `rotate_rect_object`：验证 rotate。
7. `flip_rect_object`：验证 flip。
8. `fill_center_hole`：验证 fill。
9. `crop_center_cell`：验证 `1x1` 中心裁剪。
10. `crop_center_bbox`：验证中心对象 bbox 裁剪。

### 7.2 固定 smoke 样例

首批 smoke 样例固定为：

1. `Copy1`：文件路径 [phase1/datasets/raw/ConceptARC/corpus/Copy/Copy1.json](phase1/datasets/raw/ConceptARC/corpus/Copy/Copy1.json)
2. `Center1`：文件路径 [phase1/datasets/raw/ConceptARC/corpus/Center/Center1.json](phase1/datasets/raw/ConceptARC/corpus/Center/Center1.json)
3. `Center2`：文件路径 [phase1/datasets/raw/ConceptARC/corpus/Center/Center2.json](phase1/datasets/raw/ConceptARC/corpus/Center/Center2.json)

使用规则：

1. Phase 0-2 只允许读取 `Copy1`、`Center1` 和 `Center2` 的 train 部分做人工调试。
2. Phase 3 第一个端到端 smoke 必须先跑 `Copy1`。
3. Phase 4 之后必须把 `Center1` 和 `Center2` 都加入回归集合。

### 7.3 首批回归任务

固定的首批回归集合为：

1. `Copy1`
2. `Copy2`
3. `Copy5`
4. `Center1`
5. `Center2`
6. `Center3`

要求：

1. 每次修改 Layer 2、Layer 3、Layer 4 任一文件后，至少回归这 6 个任务。
2. 不允许用诊断任务替代这 6 个训练任务。

## 8. 测试文件要求

### 8.1 test_loader.py

必须覆盖：

1. 训练任务计数 = 12。
2. 诊断任务不在默认加载列表。
3. `Copy1`、`Center1` 能被正确解析出 train/test pair 数量。

### 8.2 test_layer1.py

必须覆盖：

1. cc4 分割。
2. cc8 分割。
3. whole_grid 分割。
4. bbox 与 center 属性计算。
5. `relative_position` 与 `alignment` 提取。

### 8.3 test_layer2.py

必须覆盖：

1. 像素重合匹配优先级。
2. 颜色+形状匹配。
3. 最优二部匹配。
4. 全失败返回空列表。
5. `alignment_id` 在 transform/constraint 中不丢失。
6. `generate_candidate_transforms` 能为 Copy 风格样例生成 `copy ; on_copy: translate(...)` 候选。
7. `generate_candidate_transforms` 能为 Center 风格样例生成 `fill(..., mode=center_cell)` 候选。
8. 当 Copy 风格样例的观测位移等于 `input_width` 或 `input_height` 时，`generate_candidate_transforms` 能生成对应符号参数版本。
9. `generate_candidate_transforms` 能为中心对象抽取类样例生成 `crop[target=center_object,mode=tight_bbox]` 候选，并为中心对象删除类样例生成 `delete[target=center_object]` 候选。
10. `generate_candidate_transforms` 能为单源对象中心放置类样例生成 `smallest_object` / `rare_color_object` 加 `to_input_center_*` 或 `to_largest_object_center_*` 的候选。
11. `generate_candidate_transforms` 能为 Center4 一类样例生成 `delete[target=all,mode=input_center_component]` 候选。
12. `generate_candidate_transforms` 能为 Center5 / Center6 一类样例生成 `translate[target=all,mode=rare_color_motif_to_largest_component_center]` 候选。

### 8.4 test_layer3.py

必须覆盖：

1. `Hypothesis` 不跨对齐混搭。
2. 强弱约束分区。
3. 描述长度计算。
4. 等价类归并保留成员。
5. 代表元选择规则。
6. 回退评分在主排序相同条件下会压制语义空转的 `copy` 块，并把罚分写入调试信息。

### 8.5 test_layer4.py

必须覆盖：

1. 八种原语的确定性执行。
2. `fill` 与 `crop` 的受限语义。
3. 裸 `copy` 被拒绝。
4. 禁用控制流被拒绝。
5. 渲染覆盖顺序、有限尺寸扩张与中心裁剪。
6. `translate` 能正确执行 `input_width`、`input_height`、`object_width`、`object_height` 这组有限符号参数及其带符号版本。
7. `center_object`、`smallest_object`、`rare_color_object` 三个 selector 能被确定性解析。
8. `translate` 能正确执行 `to_input_center_*` 与 `to_largest_object_center_*`。
9. `crop_selected_bbox` 模式下只输出被裁剪对象。

### 8.6 test_layer5.py

必须覆盖：

1. 像素精度计算。
2. 约束检查输出。
3. 失败分类。
4. Attribution 结构完整性。

### 8.7 test_runner.py

必须覆盖：

1. 单任务运行写出调试产物。
2. 批量运行只消费训练任务。
3. `summary.json` 至少包含精确求解数、失败类型分布、每层耗时统计。

## 9. 每阶段的编码完成定义

只有同时满足以下条件，才允许进入下一阶段：

1. 当前阶段对应测试文件全部通过。
2. 当前阶段新增公共接口已在本清单中兑现。
3. 没有引入 Step 2 能力。
4. 没有通过样例级 ad-hoc 特判让测试通过；若引入任务族级受限 mode，必须先在正文和附录里写明其固定语义、触发条件和非目标能力，再计入通过标准。

## 10. codex 执行注意事项

codex 按本清单实现时，必须遵守以下规则：

1. 不要一次性生成全部文件后再统一修；必须按 Phase 顺序落地并验证。
2. 每完成一个 Phase，就先补齐该 Phase 的测试再进入下一阶段。
3. 如果某个 Center 任务需要当前 DSL 子集外的能力，不要偷偷扩 DSL；应先标记为 `ABSTRACTION_FAIL`，再回到文档层判断是否真越界。
4. 如果为了通过某个训练样例需要写死 task id、固定坐标、固定颜色、固定宽度，视为违规实现。
5. 如果出现“主架构允许，但附录未放开”的能力，以附录为准，禁止实现。
6. 当前 Step 1 收尾阶段，只允许继续优化 `Center5` 与 `Center6`。`Copy2`、`Copy3`、`Copy4`、`Copy5`、`Copy6`、`Center3` 不再作为 Step 1 实现目标；若分析显示它们需要更细感知、对象组复制、块级重复或 richer object 表示，则直接记为 Step 2 入口，不继续编码。

## 11. 交付检查表

最终交付前，必须逐项勾选：

1. `src/step1` 与 `tests/step1` 目录完整存在。
2. 12 个训练任务能被默认批量加载。
3. 诊断任务未进入默认运行路径。
4. 八个原语单测全部通过。
5. Layer 1、2、3、4、5、runner 各自都有独立测试文件。
6. `Attribution` 输出包含 `selected_constraints` 与 `search_stats`。
7. `summary.json` 可生成。
8. 代码未引入 Step 2+ 能力。
9. 未使用样例级 ad-hoc 特判；若使用任务族级受限 mode，必须已被文档显式登记，且不能被宣称为一般统一抽象。
10. 当前收尾阶段若继续提交实现，只面向 `Center5` 与 `Center6`；其余剩余失败任务已被明确归档为 Step 2 问题，不再以 Step 1 名义继续扩边界。
11. 若 `Center5` 与 `Center6` 被继续实现，则验收同时检查两点：
    - 结果上，优先目标是两题精确求解并把 batch `exact_solved` 提升到至少 6。
    - 边界上，整个实现过程不得引入新的分割方案、关系类型、primitive 或一般 repeat / 对象组复制能力；若为该任务族补入固定语义的受限 mode，则必须明确标注其仍属于任务族级 patch，而不是更一般的统一解。
