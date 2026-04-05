# 第一阶段 Step 2 实现任务分解清单

> 版本：v0.1
>
> 状态：Step 2a 已完成（8/12）；Step 2b 待实施
>
> 作用：把 [Step2实现设计-0v1.md](Step2实现设计-0v1.md) 和 [Step2最小接口与任务清单附录-0v1.md](Step2最小接口与任务清单附录-0v1.md) 压缩成可直接编码的任务清单，供 codex 按顺序落地。

## 1. 使用方式

本清单只服务于 Step 2 编码落地，不再讨论架构方向。

Step 2 的实现前提固定如下：

1. `phase1/src/step1/` 已是冻结基线，只允许复制，不允许修改。
2. Step 2 代码必须全部落在 `phase1/src/step2/`。
3. 编码顺序必须先完成 Step 2a，再进入 Step 2b；不允许把 4 个新概念组和 Step 2a 改动混写在一起。
4. 若本清单与 [Step2最小接口与任务清单附录-0v1.md](Step2最小接口与任务清单附录-0v1.md) 冲突，以附录为准。
5. 若本清单与 [Step2实现设计-0v1.md](Step2实现设计-0v1.md) 冲突，以附录优先、正文次之，本清单必须回改，不允许在代码里自行解释。
6. 若编码过程中发现某任务需要 merge、repeat、group copy、排序模型、知识写回等 Step 3 能力，必须停止并标记为越界，不允许先实现再回头解释。

## 2. 硬边界

编码过程中必须始终满足以下硬边界：

1. Step 2a 只允许使用 Copy1-6 与 Center1-6 训练任务；Copy7-10 与 Center7-10 全程不可见。
2. Step 2b 只允许使用 MoveToBoundary1-6、ExtendToBoundary1-6、ExtractObjects1-6、CleanUp1-6；7-10 全程不可见。
3. 只允许 `cc4`、`cc8`、`whole_grid`、`bg_fg` 四种分割方案进入默认执行路径；`nested` 只允许在 Step 2a 验收后、且确认 `bg_fg` 不足时再启用。
4. 只允许一对一对象对齐；`merge_groups` 与 `split_groups` 必须恒为空列表。
5. 只允许 `copy`、`translate`、`rotate`、`flip`、`delete`、`recolor`、`fill`、`crop`、`extend_to_boundary` 进入候选与执行。
6. 不允许 ForEach、If、group_by、merge、partition、construct_grid、tile、sort、conditional_map、scale、路径 B。
7. 不允许样例级 ad-hoc 特判，不允许为某个任务新增未登记的受限 mode。
8. `Hypothesis` 必须继续显式区分 `alignment_id` 与 `alignment_family_id`。
9. `Attribution` 必须继续保留 `selected_plan`、`selected_alignment`、`selected_alignment_family`、`selected_program`、`selected_constraints`、`search_stats`，并新增 `concept_group`。
10. `constraint_subset` 与 `selected_constraints` 必须继续保留 `strong` / `weak` 两个 key，即使 `weak` 为空。
11. 输出尺寸规则仍只允许四类：`preserve_input_size`、`fit_transformed_extent`、`crop_selected_bbox`、`crop_center_cell`。
12. Step 2 完成的最低归因粒度是区分“分割不足”和“原语表达力不足”；若仍无法稳定区分“对齐失败”和“程序表达力不足”，可以完成 Step 2，但不得据此宣布可进入 Step 3。

## 3. 目录落地目标

编码开始时先复制目录，完成后至少应有：

```text
phase1/
├── src/
│   ├── step1/                        # 冻结，不修改
│   └── step2/
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
│   └── step2/
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
    └── step2/
        ├── debug/
        └── reports/
```

测试目录必须一开始就建立，不允许“代码先写完，最后再补测试”。

## 4. 全局编码约定

### 4.1 复制与演进规则

1. 首次创建 Step 2 时，完整复制 `phase1/src/step1/` 到 `phase1/src/step2/`。
2. Step 2 的实现默认是在 Step 1 代码基础上做最小增量修改，不重写整层逻辑。
3. `step2/` 内部导入统一改为 `phase1.src.step2.*`。
4. `step1/utils/` 若无需修改，可继续复用；layer1-5、runner、config、models、loader 必须在 `step2/` 内独立维护。

### 4.2 运行命令

默认测试命令固定为：

```bash
python3 -m unittest discover -s phase1/tests/step2 -p "test_*.py"
```

默认批量运行命令固定为：

```bash
python3 -m phase1.src.step2.runner.batch_runner
```

若需要新增阶段参数或概念组过滤，只允许扩展 `batch_runner.py` 的 CLI，不允许绕开 runner 直接写临时脚本。

### 4.3 稳定 ID 与兼容性

1. 延续 Step 1 的稳定 ID 规则，不重定义 `plan_id`、`alignment_id`、`alignment_family_id`。
2. 新增 `bg_fg` 与 `nested` 时，`plan_id` 必须直接使用方法名：`bg_fg`、`nested`。
3. `Object.id` 的 tie-break 语义必须稳定，供 `largest_object`、`smallest_object`、`center_object`、`rare_color_object` 并列时使用。
4. `Alignment.alignment_id` 继续表达 pair 级 provenance，不得借用为 family 级标识。

## 5. 必须修改的公共接口

本节只列 Step 2 相对 Step 1 必须发生变化的接口；未列出的接口默认沿用 Step 1。

### 5.1 data/models.py

必须完成以下变更：

1. `SegmentationPlan` 新增字段：`bg_color: int | None`。
2. `SegmentationPlan.method` 的允许值扩展为：`cc4 | cc8 | whole_grid | bg_fg | nested`。
3. `Attribution` 新增字段：`concept_group: str | None`。
4. 所有新增字段必须保持可 JSON 序列化。

不得变更：

1. `Hypothesis` 结构。
2. `Alignment` 结构。
3. `SearchStats` 结构。
4. `merge_groups`、`split_groups` 的存在性。

### 5.2 config.py

必须导出或更新以下常量：

```python
STEP2_CONCEPT_GROUPS
STEP2_TRAIN_TASKS
STEP2_DIAGNOSTIC_TASKS
ALLOWED_SEGMENTATION_METHODS
ALLOWED_PRIMITIVES
ALLOWED_OUTPUT_SIZE_RULES
STEP2_BEAM_SIZE
DEFAULT_OUTPUT_DIR
```

要求：

1. `STEP2_CONCEPT_GROUPS = ["Copy", "Center", "MoveToBoundary", "ExtendToBoundary", "ExtractObjects", "CleanUp"]`。
2. `STEP2_TRAIN_TASKS` 只覆盖 1-6。
3. `STEP2_DIAGNOSTIC_TASKS` 只覆盖 7-10，不提供默认批量消费入口。
4. `ALLOWED_SEGMENTATION_METHODS` 默认包含 `cc4`、`cc8`、`whole_grid`、`bg_fg`；`nested` 必须通过显式开关启用，默认关闭。
5. `ALLOWED_PRIMITIVES` 默认包含 `extend_to_boundary`。
6. `STEP2_BEAM_SIZE` 初始值设为 64；若后续上调，必须通过配置改，不允许散落常量。

### 5.3 data/loader.py

必须导出：

```python
def load_task(concept: str, task_id: str, file_path: str) -> ArcTask: ...
def load_step2_train_tasks() -> list[ArcTask]: ...
def load_step2_task_ids() -> list[str]: ...
```

要求：

1. `load_step2_train_tasks()` 默认返回 6 个概念组的 1-6 训练任务。
2. 不提供默认批量加载诊断任务的入口函数。
3. 概念组路径必须完全由 `config.py` 派生，不允许在 loader 中硬编码第二份任务清单。

### 5.4 layer1/perception.py

必须保留并扩展：

```python
def build_segmentation_plan(grid: Grid, method: str) -> SegmentationPlan: ...
def perceive_grid(grid: Grid) -> PerceptionOutput: ...
```

要求：

1. 新增 `bg_fg` 分割。
2. `bg_fg` 规则固定为“最高频颜色为背景；并列时取数值最小颜色”。
3. `bg_fg` 方案下只对非背景色像素做 4 连通分量提取。
4. 非 `bg_fg` 方案下 `bg_color = None`。
5. `nested` 只在开关打开时进入 `perceive_grid()`；默认不启用。

### 5.5 layer1/relations.py

必须新增并稳定输出：

1. `adjacency`
2. `containment`

要求：

1. `adjacency` 使用 4 邻域定义。
2. `containment` 以 bbox 完全包含定义。
3. 原有相对位置/对齐关系不得删除。

### 5.6 layer2/alignment.py

必须保留：

```python
def align_objects(...) -> list[Alignment]: ...
```

要求：

1. 不新增多对一或一对多语义。
2. `bg_fg` 方案下，只在前景对象集上做对齐。
3. 对齐方法仍只允许像素重合、颜色+形状、二部匹配三类。

### 5.7 layer2/diff.py

必须扩展差异类型识别，至少覆盖：

1. Step 1 现有差异类型。
2. `位置变化（边界对齐）`
3. `形状延伸`
4. `对象消失 + 尺寸缩小`
5. `噪声像素消失`

要求：

1. Step 2a 不为 Copy/Center 新增概念级特判差异类型。
2. Step 2b 新概念组的候选模板必须由这里识别的差异类型驱动。

### 5.8 layer2/constraints.py

必须保留：

```python
def extract_constraints(...) -> list[CandidateConstraint]: ...
def partition_constraints(...) -> dict[str, list[str]]: ...
def observed_size_rules(...) -> list[str]: ...
```

要求：

1. 继续支持四类输出尺寸规则。
2. 局部一致性和计数守恒只允许作为按需启用的候选约束，不得升级为全局硬编码过滤。
3. `crop_selected_bbox` 的选择器语义必须兼容 `center_object` 和 `largest_object`。

### 5.9 layer2/sketches.py

必须保留：

```python
def generate_candidate_transforms(...) -> list[CandidateTransform]: ...
def build_candidate_set(...) -> CandidateSet: ...
```

必须完成以下扩展：

1. Step 2a：为 `bg_fg` 方案补充 `largest_object` 候选。
2. Step 2a：copy 类候选与 delete 类候选都继续生成，不允许为了提高命中率而删除某类候选。
3. Step 2b：新增以下模板族：

```text
# MoveToBoundary
translate[target=X, dx=to_boundary_dx, dy=to_boundary_dy]
translate[target=X, dx=to_nearest_object_dx, dy=to_nearest_object_dy]

# ExtendToBoundary
extend_to_boundary[target=X, direction=D]

# ExtractObjects
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
crop[target=largest_object, mode=tight_bbox]

# CleanUp
delete[target=noise_objects]
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
```

4. `foreground_objects`、`noise_objects` 只允许用于接受对象集的原语。
5. 不允许在 DSL 中引入“从对象集再选最大者”这种二次归约语义。

### 5.10 layer3/scoring.py

必须保留：

```python
def description_length(hypothesis: Hypothesis) -> int: ...
def pre_priority(hypothesis: Hypothesis) -> tuple[float, int]: ...
```

必须完成以下扩展：

1. `description_length()` 自动兼容 `extend_to_boundary` 和 3 步程序。
2. `pre_priority()` 进入 Step 2b 前必须沿用 Step 2a 已落地的评分基线，不要求回退到早期设计草案中的“差异类型一致性奖励”版本。当前基线为语义一致性 bonus：`copy +0.35`，`delete / translate / crop` 各 `+0.15`；若 Step 2b 需要新增奖励规则，只允许在这一基线上做增量扩展，并同步回归 Step 2a 的 12 个任务。
3. 若需要使用 beam 调整，只能通过 `STEP2_BEAM_SIZE` 配置实现。

### 5.11 layer3/selector.py

必须保留：

```python
def beam_priority_key(hypothesis: Hypothesis) -> ...
def apply_hypothesis_beam(...) -> list[Hypothesis]: ...
def select_best_hypothesis(...) -> Hypothesis | None: ...
```

要求：

1. 继续支持 rendered output cache。
2. 继续对等价假设做分组。
3. 不引入学习型排序器。

### 5.12 layer4/dsl.py

必须扩展 Step 1 DSL，允许：

1. 程序最大深度从 2 步提升到 3 步。
2. `PrimitiveOp` 新增 `extend_to_boundary`。
3. `direction` 参数允许 `up/down/left/right/nearest_boundary`。

不得新增：

1. ForEach
2. If
3. 表达式树
4. 用户自定义参数名

### 5.13 layer4/executor.py

必须保留：

```python
def execute_program(...) -> list[ObjectData]: ...
```

必须完成以下变更：

1. `_background_color()` 改为优先读取 `SegmentationPlan.bg_color`，缺省回退 0。
2. `_resolve_target_ids()` 支持 `largest_object`、`foreground_objects`、`noise_objects`、`boundary_adjacent`。
3. 新增 `extend_to_boundary` 执行逻辑。
4. `nearest_boundary` 的 tie-break 必须固定；若多个边界等距，顺序写死为 `up > down > left > right`，不允许运行时漂移。
5. 对象集选择器传给单对象原语时必须报错或在候选生成阶段被阻断，不允许静默降级。

### 5.14 layer4/render.py

必须继续保留四类输出尺寸规则，并完成以下扩展：

1. 背景色填充改为使用 `SegmentationPlan.bg_color`。
2. `crop_selected_bbox` 必须兼容 `largest_object` 场景。
3. ExtractObjects 的裁剪输出必须以被选主体 bbox 为新画布。

### 5.15 layer5/verify.py

必须保留：

```python
def pixel_accuracy(predicted: Grid, target: Grid) -> float: ...
def verify_constraints(predicted: Grid, hypothesis: Hypothesis) -> tuple[list[str], list[str]]: ...
def classify_failure(...) -> tuple[str, str | None]: ...
```

要求：

1. `failure_type = SELECTION_FAIL` 时，`failure_detail` 必须使用硬枚举：`PLAN_ERROR`、`ALIGNMENT_ERROR`、`CONSTRAINT_SUBSET_ERROR`、`PROGRAM_ERROR`。
2. 其他 failure_type 可继续使用自由文本，但必须非空且可读。
3. Step 2 完成时，归因至少能区分“分割不足”和“原语表达力不足”。

### 5.16 layer5/attribution.py

必须保留：

```python
def build_attribution(...) -> Attribution: ...
```

要求：

1. 新增 `concept_group` 填充逻辑。
2. Step 2b 的新概念组必须正确写入概念组名。
3. 未解任务的 `failure_detail` 必须非空。

### 5.17 runner/task_runner.py

必须保留：

```python
def run_task(task: ArcTask, output_dir: str | Path) -> Attribution: ...
```

必须完成以下变更：

1. 继续按照 Layer1 → Layer2 → Layer3 → Layer4 → Layer5 主链运行。
2. 继续构造 `CandidateSet`、`Hypothesis`、rendered train outputs 和 `SearchStats`。
3. 引入 Step 2 后，不允许破坏 Step 1 的 6/12 基线。
4. 当使用 `bg_fg` 或 `noise_objects` 时，必须把相关诊断信息写入调试输出。

### 5.18 runner/batch_runner.py

必须保留并扩展：

```python
def run_step2_batch(output_dir: str | Path) -> list[Attribution]: ...
def build_summary(attributions: list[Attribution]) -> dict: ...
def main() -> None: ...
```

必须支持：

1. `--group <ConceptGroup>`
2. `--stage 2a`
3. `--stage 2b`

汇总输出必须包含：

1. 概念组聚合统计。
2. 相对 Step 1 基线的回归标记。
3. Step 2b 每组引入后的回归标记。

## 6. 编码顺序

### Phase 0：复制骨架与配置入口

1. 复制 `phase1/src/step1/` 到 `phase1/src/step2/`。
2. 建立 `phase1/tests/step2/` 目录，初始复制 Step 1 测试骨架。
3. 修改 `step2/` 内部导入路径。
4. 创建 `step2/config.py` 的 Step 2 常量。
5. 创建 `step2/data/loader.py` 的 Step 2 任务加载入口。

完成定义：`python3 -m phase1.src.step2.runner.batch_runner` 至少能加载任务列表并失败在未实现逻辑，而不是导入错误。

### Phase 1：先做接口扩展，不改搜索语义

1. 修改 `data/models.py`，加入 `SegmentationPlan.bg_color` 和 `Attribution.concept_group`。
2. 更新所有 dataclass 的 JSON 转换逻辑，确保新增字段可落盘。
3. 在不启用新能力时，保证 Step 2 代码跑出的行为与 Step 1 一致。

完成定义：Step 2 代码在只启用 Step 1 能力时，能跑通 Step 1 旧测试骨架。

### Phase 2：做 Step 2a 的 Layer 1

1. 在 `layer1/perception.py` 实现 `bg_fg`。
2. 在 `layer1/relations.py` 实现 `adjacency` 与 `containment`。
3. 默认不要启用 `nested`。
4. 为 `bg_fg` 补最小单元测试：背景色 tie-break、前景对象提取、非 bg_fg 时 `bg_color is None`。

完成定义：Center3 所需的 `bg_fg` 感知链已可单独测试，旧 cc4/cc8/whole_grid 行为不退化。

### Phase 3：做 Step 2a 的 Layer 4

1. 在 `dsl.py` 扩展 3 步程序和 `extend_to_boundary` 语法，但此阶段先不生成该原语候选。
2. 在 `executor.py` 修复 `_background_color()`，补 `largest_object` 选择器解析。
3. 在 `render.py` 接入动态背景色。
4. 保持 `extend_to_boundary` 的执行器函数可用，但先只做单元测试，不接入候选生成。

完成定义：使用手写 program 可正确执行 `bg_fg` + `largest_object` + 动态背景色链路。

### Phase 4：做 Step 2a 的 Layer 2

1. 让 `alignment.py` 兼容 `bg_fg` 方案。
2. 让 `sketches.py` 为 `bg_fg` 生成 `largest_object` 候选。
3. 保持 Copy/Center 现有候选族不丢失。
4. 暂不引入 Step 2b 新概念组模板。

完成定义：Copy2、Center3 至少能生成与 Step 2 设计一致的新候选，而不是仍只有 Step 1 候选。

### Phase 5：做 Step 2a 的 Layer 3 / Layer 5

1. 在 `scoring.py` 中固化 Step 2a 已落地的语义一致性 bonus 基线，并禁止为进入 Step 2b 回退 Step 2a 评分逻辑。
2. 保持 `selector.py` 的 beam、等价分组、fallback 机制。
3. 在 `verify.py` 固化 `SELECTION_FAIL` 的 `failure_detail` 枚举。
4. 在 `attribution.py` 中加入 `concept_group` 写入。

完成定义：Step 2a 的未解任务都有非空、可读、口径一致的归因输出。

### Phase 6：先做 Step 2a 里程碑，并形成 Step 2b 准入结论

1. 跑 Copy1-6 + Center1-6。
2. 先检查基线是否仍是至少 6/12。
3. 再检查是否达到 Step 2a 的正式门槛：总计 ≥9/12 且基线不回归。
4. 若未达标，优先排查 Center3 的 `bg_fg` 链路，再排查 Copy2 的选择器问题，再看 pre_priority 与 beam。
5. 此阶段不得引入 4 个新概念组代码来“顺手修” Step 2a。

完成定义：Step 2a 达标，或明确形成“有条件通过”的项目结论并写入报告。若按“有条件通过”放行 Step 2b，则必须同时写明 Copy3-6 不回流 Step 2b 修复，而是登记为 Step 3 提前引入能力。

### Phase 7：按概念组逐组引入 Step 2b 能力

Step 2b 必须严格按设计文档规定的顺序引入：MoveToBoundary → ExtendToBoundary → ExtractObjects → CleanUp。不得把 4 组能力一次性打通后再统一验收。

#### Phase 7A：MoveToBoundary

1. 在 `sketches.py` 加入 MoveToBoundary 模板族：

```text
translate[target=X, dx=to_boundary_dx, dy=to_boundary_dy]
translate[target=X, dx=to_nearest_object_dx, dy=to_nearest_object_dy]
```

2. 在 `diff.py` 加入“位置变化（边界对齐）”差异类型。
3. 在 `executor.py` 打通 `to_boundary_*` 与 `to_nearest_object_*`。
4. 在 `constraints.py` 中按需启用局部一致性，但不要默认强制开启。
5. 运行 MoveToBoundary1-6，并回跑 Step 2a 的 12 个任务。

子阶段完成定义：MoveToBoundary 达到 **≥3/6**，且 Step 2a 结果不回归。

#### Phase 7B：ExtendToBoundary

1. 在 `sketches.py` 加入 ExtendToBoundary 模板族：

```text
extend_to_boundary[target=X, direction=D]
```

2. 在 `diff.py` 加入“形状延伸”差异类型。
3. 在 `executor.py` 打通 `extend_to_boundary` 原语。
4. 运行 ExtendToBoundary1-6，并回跑 Step 2a + MoveToBoundary。

子阶段完成定义：ExtendToBoundary 达到 **≥3/6**，且前序结果不回归。

#### Phase 7C：ExtractObjects

1. 在 `sketches.py` 加入 ExtractObjects 模板族：

```text
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
crop[target=largest_object, mode=tight_bbox]
```

2. 在 `diff.py` 加入“对象消失 + 尺寸缩小”差异类型。
3. 在 `executor.py` 打通 `noise_objects` 与 `largest_object` 组合链路。
4. 在 `constraints.py` 中按需启用计数守恒，但不要把“输出必须为 1 个对象”写成全局硬编码。
5. 仅当确认 `bg_fg` 不足以覆盖该组任务时，才允许启用 `nested`。
6. 运行 ExtractObjects1-6，并回跑 Step 2a + MoveToBoundary + ExtendToBoundary。

子阶段完成定义：ExtractObjects 达到 **≥2/6**，且前序结果不回归。

#### Phase 7D：CleanUp

1. 在 `sketches.py` 加入 CleanUp 模板族：

```text
delete[target=noise_objects]
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
```

2. 在 `diff.py` 加入“噪声像素消失”差异类型。
3. 在 `constraints.py` 中按需启用计数守恒与局部一致性。
4. 若经过验证确有必要，才允许在本子阶段为 CleanUp 启用 `nested`。
5. 运行 CleanUp1-6，并回跑 Step 2a + 全部前序组。

子阶段完成定义：CleanUp 达到 **≥2/6**，且前序结果不回归。

### Phase 8：做 Step 2b 的 runner、遥测与报告

1. 收口 `batch_runner.py`，支持 `--group`、`--stage 2a`、`--stage 2b`，并确保它能复现 Phase 7A-7D 的逐组验收流程。
2. 在 `summary.json` / `summary.md` 输出概念组聚合。
3. 实现 `regression_flags`。
4. 把 `bg_color`、`noise_objects` 诊断写入 debug 输出。

完成定义：可按概念组和阶段重复跑批，并自动标记回归。进入 Phase 8 前，不得把这些能力误记为当前已完成基线。

### Phase 9：全量回归与收口

1. 跑完整 36 个训练任务。
2. 检查 Step 2a 总计 ≥9/12 且基线不回归。
3. 检查 4 个新增概念组是否达到各自最低下限：MoveToBoundary ≥3/6、ExtendToBoundary ≥3/6、ExtractObjects ≥2/6、CleanUp ≥2/6。
4. 检查所有未解任务都有合理归因。
5. 检查 `step1/` 无改动。

完成定义：满足 Step 2 文档中的整体验收门槛。

## 7. 首批测试样例

### 7.1 合成单元样例

优先补以下合成样例：

1. `bg_fg` 背景色并列最高频时，取数值最小颜色。
2. `adjacency` 与 `containment` 的正例/反例。
3. `largest_object`、`boundary_adjacent`、`noise_objects` 的 tie-break 与选择边界。
4. `extend_to_boundary` 在 `up/down/left/right/nearest_boundary` 五种方向上的停止条件；`nearest_boundary` 等距时按 `up > down > left > right`。
5. `crop_selected_bbox` 在 `largest_object` 目标上的输出尺寸。
6. `SELECTION_FAIL` 四种 `failure_detail` 枚举。

### 7.2 固定 smoke 样例

至少固定以下真实任务作为 smoke：

1. Copy1
2. Center3
3. MoveToBoundary1
4. ExtendToBoundary1
5. ExtractObjects1
6. CleanUp1

### 7.3 首批回归任务

必须持续回跑：

1. Step 1 原成功任务：Copy1、Center1、Center2、Center4、Center5、Center6。
2. Step 2a 新增重点任务：Copy2、Center3。
3. Step 2b 每组至少 1 个已成功任务。

## 8. 测试文件要求

### 8.1 test_loader.py

至少覆盖：

1. Step 2 六个概念组的训练任务列表加载。
2. 诊断任务不被默认入口加载。

### 8.2 test_layer1.py

至少覆盖：

1. `bg_fg` 对非零背景色任务的分割。
2. `bg_color` tie-break。
3. `adjacency`。
4. `containment`。
5. `nested` 开关关闭时不参与默认输出。

### 8.3 test_layer2.py

至少覆盖：

1. `bg_fg` 方案下的对齐。
2. Step 2b 新差异类型的识别。
3. `largest_object` 候选生成。
4. `foreground_objects` / `noise_objects` 不会进入单对象原语。

### 8.4 test_layer3.py

至少覆盖：

1. Step 2a 已落地的语义一致性 bonus 会维持 copy / delete / translate / crop 候选的既有优先级关系。
2. Step 2 仍能做 beam 截断与等价假设分组。

### 8.5 test_layer4.py

至少覆盖：

1. 动态背景色渲染。
2. `largest_object` / `boundary_adjacent` / `noise_objects` 目标解析。
3. `extend_to_boundary` 执行。
4. 3 步 DSL 程序解析与执行。

### 8.6 test_layer5.py

至少覆盖：

1. `concept_group` 填充。
2. `SELECTION_FAIL` 的 `failure_detail` 枚举约束。
3. 未解任务 `failure_detail` 非空。

### 8.7 test_runner.py

至少覆盖：

1. `--stage 2a`。
2. `--stage 2b`。
3. `--group`。
4. `summary.json` / `summary.md` 概念组聚合。
5. `regression_flags` 输出。

说明：以上 5 项属于 Step 2b Phase 8 的测试目标，不代表当前 Step 2a 基线已具备这些 runner / report 能力。

## 9. 每阶段的编码完成定义

1. Phase 0 完成：Step 2 包可导入，测试骨架可发现。 ✅
2. Phase 1 完成：接口扩展后，Step 2 在关闭新能力时不破坏 Step 1 行为。 ✅
3. Phase 2 完成：`bg_fg`、`adjacency`、`containment` 单测通过。 ✅
4. Phase 3 完成：动态背景色渲染和 `largest_object` 执行链路通过单测。 ✅
5. Phase 4 完成：Copy2、Center3 已能产生符合 Step 2 设计的新候选。 ✅
6. Phase 5 完成：归因口径稳定，`SELECTION_FAIL` 枚举落地。 ✅
7. Phase 6 完成：Step 2a 达标，或形成明确的 Step 2b 准入结论。 ✅ **当前状态为 8/12，未达 ≥9/12 原始门槛，但已按“有条件通过”验收放行 Step 2b；Copy3-6 不在 Step 2b 内扩边界修复，已登记为 Step 3 提前引入能力。**
8. Phase 7A 完成：MoveToBoundary 达到 ≥3/6，且 Step 2a 不回归。
9. Phase 7B 完成：ExtendToBoundary 达到 ≥3/6，且前序结果不回归。
10. Phase 7C 完成：ExtractObjects 达到 ≥2/6，且前序结果不回归。
11. Phase 7D 完成：CleanUp 达到 ≥2/6，且前序结果不回归。
12. Phase 8 完成：批量报告、回归标记、必需遥测都能自动落盘。
13. Phase 9 完成：满足 Step 2 整体验收。

## 10. codex 执行注意事项

1. 一次只做一个 Phase 或子阶段，不允许跨 Phase / 子阶段大包改动。
2. 每完成一个 Phase 就先补该 Phase 的最小测试，再进入下一个 Phase。
3. 在 Step 2a 的准入结论明确前，不允许以“顺便支持 Step 2b”为由改 DSL、候选或约束边界；当前既然已按“有条件通过”放行 Step 2b，则 Step 2b 仍不得承接 Copy3-6 的边界外修复。
4. `nested` 是延后开关，不是默认能力；只有确认 `bg_fg` 不足时才实现到默认路径。
5. 不允许把对象集选择器静默传给单对象原语。
6. 不允许为了抬成功率删减失败归因、跳过 debug 输出或手工挑选 summary 内容。

## 11. 交付检查表

交付前必须逐项确认：

1. `phase1/src/step1/` 未被修改。 ✅
2. `phase1/src/step2/` 已存在独立实现。 ✅
3. Step 2a 原始正式门槛满足：总计 ≥9/12 且基线不回归。 ⚠️ **当前为 8/12，未达原始硬门槛；但已按“有条件通过”验收，允许进入 Step 2b。注意：Copy3-6 不回流 Step 2b，相关能力已登记为 Step 3 提前引入能力。**
4. 4 个新增概念组达到最低求解下限：MoveToBoundary ≥3/6、ExtendToBoundary ≥3/6、ExtractObjects ≥2/6、CleanUp ≥2/6。 _(Step 2b 范围，待实施)_
5. Step 2b 每引入一组后，前序组和 Step 2a 结果均未回归。 _(Step 2b 范围，待实施)_
6. `bg_color`、`regression_flags`、`noise_objects` 诊断已写入调试输出。 ⚠️ **仅 `bg_color` 已在当前基线落地；`regression_flags` 与 Step 2b 级别的 `noise_objects` 诊断仍属于 Phase 8 待完成项。**
7. 所有未解训练任务的 `failure_detail` 非空且合理。 ✅
8. `summary.json` 与 `summary.md` 已输出概念组聚合。 ⚠️ **当前 summary 已落盘，但概念组聚合仍属于 Phase 8 待完成项。**
9. `SELECTION_FAIL` 的 `failure_detail` 只使用四个硬枚举值。 ✅
10. 测试通过（78 tests, 0 failures）：

```bash
python3 -m unittest discover -s phase1/tests/step2 -p "test_*.py"
```

11. 批量运行可复现：

```bash
python3 -m phase1.src.step2.runner.batch_runner
```