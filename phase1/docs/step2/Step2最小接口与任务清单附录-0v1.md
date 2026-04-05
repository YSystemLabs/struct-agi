# 第一阶段 Step 2 最小接口与任务清单附录

> 版本：v0.1
>
> 状态：草案
>
> 作用：为 Step 2 冻结任务边界、最小接口、对齐白名单与运行遥测，消除实现歧义。

## 1. 文档定位

本附录是 [Step1最小接口与任务清单附录-0v1.md](../step1/Step1最小接口与任务清单附录-0v1.md) 的增量版本，**只描述 Step 2 相对于 Step 1 的变更与新增**。凡本附录未提及的部分，沿用 Step 1 附录的定义。

本附录引用的算法设计来源为 [第一阶段算法架构-0v4.md](../第一阶段算法架构-0v4.md)，特别是 §3.3（分割策略）、§3.4（关系提取）、§4.2.1（原语集）、§4.3（输出尺寸推断）和 §12.2（Step 2 计划）。

Step 2 分两个子阶段：

- **Step 2a**：在 Step 1 冻结的 Copy/Center 数据上，利用新放开的能力修复 Step 1 遗留失败（目标 ≥9/12）。
- **Step 2b**：将求解器扩展到 4 个新概念组：MoveToBoundary、ExtendToBoundary、ExtractObjects、CleanUp。

凡本附录未明确放开的能力，默认不属于 Step 2。

## 2. Step 2 冻结范围

### 2.1 数据范围

Step 2 在 Step 1 数据范围上新增 4 个概念组，每组 10 个任务（6 训练 + 4 诊断）。

#### 2.1.1 Step 2a 数据（沿用 Step 1）

Step 2a 继续使用 Step 1 的 Copy1-6 与 Center1-6 共 12 个训练任务，以及 Copy7-10 与 Center7-10 共 8 个诊断任务。任务清单与路径见 Step 1 附录 §2.1，此处不重复。

#### 2.1.2 Step 2b 新增训练任务

| 概念组 | 任务 ID | 路径 |
| --- | --- | --- |
| MoveToBoundary | MoveToBoundary1 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary1.json |
| MoveToBoundary | MoveToBoundary2 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary2.json |
| MoveToBoundary | MoveToBoundary3 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary3.json |
| MoveToBoundary | MoveToBoundary4 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary4.json |
| MoveToBoundary | MoveToBoundary5 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary5.json |
| MoveToBoundary | MoveToBoundary6 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary6.json |
| ExtendToBoundary | ExtendToBoundary1 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary1.json |
| ExtendToBoundary | ExtendToBoundary2 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary2.json |
| ExtendToBoundary | ExtendToBoundary3 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary3.json |
| ExtendToBoundary | ExtendToBoundary4 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary4.json |
| ExtendToBoundary | ExtendToBoundary5 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary5.json |
| ExtendToBoundary | ExtendToBoundary6 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary6.json |
| ExtractObjects | ExtractObjects1 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects1.json |
| ExtractObjects | ExtractObjects2 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects2.json |
| ExtractObjects | ExtractObjects3 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects3.json |
| ExtractObjects | ExtractObjects4 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects4.json |
| ExtractObjects | ExtractObjects5 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects5.json |
| ExtractObjects | ExtractObjects6 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects6.json |
| CleanUp | CleanUp1 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp1.json |
| CleanUp | CleanUp2 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp2.json |
| CleanUp | CleanUp3 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp3.json |
| CleanUp | CleanUp4 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp4.json |
| CleanUp | CleanUp5 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp5.json |
| CleanUp | CleanUp6 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp6.json |

#### 2.1.3 Step 2b 新增诊断任务

诊断任务 Step 1-2 全程不可见，不得用于调参或 ad-hoc 特判：

| 概念组 | 任务 ID | 路径 |
| --- | --- | --- |
| MoveToBoundary | MoveToBoundary7 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary7.json |
| MoveToBoundary | MoveToBoundary8 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary8.json |
| MoveToBoundary | MoveToBoundary9 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary9.json |
| MoveToBoundary | MoveToBoundary10 | phase1/datasets/raw/ConceptARC/corpus/MoveToBoundary/MoveToBoundary10.json |
| ExtendToBoundary | ExtendToBoundary7 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary7.json |
| ExtendToBoundary | ExtendToBoundary8 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary8.json |
| ExtendToBoundary | ExtendToBoundary9 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary9.json |
| ExtendToBoundary | ExtendToBoundary10 | phase1/datasets/raw/ConceptARC/corpus/ExtendToBoundary/ExtendToBoundary10.json |
| ExtractObjects | ExtractObjects7 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects7.json |
| ExtractObjects | ExtractObjects8 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects8.json |
| ExtractObjects | ExtractObjects9 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects9.json |
| ExtractObjects | ExtractObjects10 | phase1/datasets/raw/ConceptARC/corpus/ExtractObjects/ExtractObjects10.json |
| CleanUp | CleanUp7 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp7.json |
| CleanUp | CleanUp8 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp8.json |
| CleanUp | CleanUp9 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp9.json |
| CleanUp | CleanUp10 | phase1/datasets/raw/ConceptARC/corpus/CleanUp/CleanUp10.json |

#### 2.1.4 Step 2 数据汇总

| 范围 | 概念组 | 训练任务数 | 诊断任务数 |
| --- | --- | --- | --- |
| Step 2a（沿用 Step 1） | Copy, Center | 12 | 8 |
| Step 2b 新增 | MoveToBoundary, ExtendToBoundary, ExtractObjects, CleanUp | 24 | 16 |
| **合计** | **6 组** | **36** | **24** |

### 2.2 分割方案范围

Step 2 在 Step 1 的三种分割方案基础上新增 `bg_fg`，并视实现需要可选启用 `nested`：

| method | 含义 | Step 1 状态 | Step 2 状态 |
| --- | --- | --- | --- |
| cc4 | 按颜色 4-连通分量分割 | 启用 | 启用 |
| cc8 | 按颜色 8-连通分量分割 | 启用 | 启用 |
| whole_grid | 将整张网格视为单一对象 | 启用 | 启用 |
| bg_fg | 频率最高颜色作为背景色，其余像素按连通分量提取前景对象 | 禁用 | **启用** |
| nested | 大区域内部递归提取子连通分量 | 禁用 | **可选启用** |
| bbox | 矩形区域检测 | 禁用 | 禁用（推迟到 Step 3） |
| repeat | 重复图样检测 | 禁用 | 禁用（推迟到 Step 3） |

`bg_fg` 启用理由：

1. Step 1 当前硬编码 `background_color = 0`，无法处理背景色非零的任务。`bg_fg` 通过频率分析自动识别候选背景色，直接解决该遗留问题（参见 Step 1 实现设计 §6.4.2 的硬编码说明）。
2. Center3 在 Step 1 中灾难性失败（2.1% 像素准确率），核心原因是 cc4/cc8 无法把嵌套在背景中的前景主体正确分离。`bg_fg` 先剥离背景后再做连通分量提取，有望改善该分割质量。
3. 架构文档 §3.3 将 `bg_fg` 列为低成本策略，适合在 Step 2 引入。

`nested` 可选启用理由：

1. 部分 ExtractObjects 和 CleanUp 任务涉及层级结构（主体对象内部嵌套子对象）。若 `bg_fg` + `cc4`/`cc8` 不足以覆盖这些任务的分割需求，则启用 `nested` 进行两级递归分割。
2. 是否实际启用由 Step 2b 实现阶段根据任务驱动的具体需求决定，此处仅放开约束边界。
3. 若最终未启用，在 Step 2 实验报告中说明理由即可。

### 2.3 Step 2 最小关系与属性范围

Step 2 在 Step 1 的关系与属性范围基础上新增邻接和包含两类关系：

| 类别 | Step 1 状态 | Step 2 状态 | 说明 |
| --- | --- | --- | --- |
| 相对位置 | 启用 | 启用 | 上下左右、对角方位 |
| 对齐 | 启用 | 启用 | 共享行、共享列、中心线对齐 |
| 邻接 | 禁用 | **启用** | 两对象是否共享边界像素 |
| 包含 | 禁用 | **启用** | 一个对象的 bbox 是否完全落在另一个内部 |
| 对称 | 禁用 | 禁用（推迟到 Step 3） | 两对象是否关于某轴或某点对称 |
| 颜色映射 | 禁用 | 禁用 | Step 2 不实现为独立 pair relation |
| 尺寸映射 | 禁用 | 禁用 | Step 2 不实现为独立 pair relation |
| 条件依赖/计数/层级 | 禁用 | 禁用（推迟到 Step 3） | |

邻接启用理由：MoveToBoundary / ExtendToBoundary 的变换语义依赖"对象与画布边界或其他对象边界的邻接关系"来确定移动/延伸方向和终止位置。

包含启用理由：ExtractObjects 需要判定"哪些对象被包含在主体区域内"以区分前景主体与背景噪声；CleanUp 需要识别"异常像素/对象是否包含在正常结构内"。

属性范围：Step 2 沿用 Step 1 的最小属性集合（dominant_color、area、height、width、center_row、center_col、bbox、canvas_height、canvas_width），不强制新增扩展属性。若 `bg_fg` 分割为对象附加 `is_foreground` 标记，该标记作为 `bg_fg` 方案内部属性，不改变通用 ObjectData schema。

### 2.4 原语范围

Step 2 在 Step 1 的 8 个原语基础上按需启用新原语：

| 原语 | Step 1 状态 | Step 2 状态 | 说明 |
| --- | --- | --- | --- |
| copy | 启用 | 启用 | |
| translate | 启用 | 启用 | |
| rotate | 启用 | 启用 | |
| flip | 启用 | 启用 | |
| delete | 启用 | 启用 | |
| recolor | 启用 | 启用 | |
| fill | 启用 | 启用 | |
| crop | 启用 | 启用 | |
| extend_to_boundary | 禁用 | **启用** | ExtendToBoundary 概念组必需 |
| scale | 禁用 | 禁用（推迟到 Step 3） | |
| conditional_map | 禁用 | 禁用（推迟到 Step 3） | |
| merge | 禁用 | **按需启用** | 若 CleanUp 需合并清理后碎片 |
| sort | 禁用 | 禁用（推迟到 Step 3） | |
| group_by | 禁用 | 禁用（推迟到 Step 3） | |
| tile | 禁用 | 禁用（推迟到 Step 3） | |
| construct_grid | 禁用 | 禁用（推迟到 Step 3） | |
| partition | 禁用 | 禁用（推迟到 Step 3） | |

`extend_to_boundary` 启用理由：架构文档 §4.2.1 定义其签名为 `Object × Direction → Object`，语义为"沿指定方向延伸对象直到触及画布边界或另一个对象边界"。这是 ExtendToBoundary 概念组的核心操作，无法用现有原语组合表达。

`merge` 按需启用理由：CleanUp 任务中，清理噪声后可能留下多个碎片对象需要合并为完整输出。是否实际启用由 Step 2b 实现阶段根据任务分析决定；若最终未启用则在实验报告中说明。

`translate` 扩展：Step 2 在 Step 1 的 translate 符号参数表基础上，新增与边界相关的位移参数：

| 参数 | 含义 | Step 1 | Step 2 |
| --- | --- | --- | --- |
| `input_width` / `input_height` | 输入画布尺寸 | 启用 | 启用 |
| `object_width` / `object_height` | 被操作对象的 bbox 尺寸 | 启用 | 启用 |
| `to_input_center_dx` / `to_input_center_dy` | 移到画布中心的位移 | 启用 | 启用 |
| `to_largest_object_center_dx` / `to_largest_object_center_dy` | 移到最大对象中心的位移 | 启用 | 启用 |
| `to_boundary_dx` / `to_boundary_dy` | 移到最近画布边界的位移 | 禁用 | **启用** |
| `to_nearest_object_dx` / `to_nearest_object_dy` | 移到最近邻对象的位移 | 禁用 | **启用** |

Step 2 仍不允许组合表达式、算术树或用户自定义参数名。

目标选择器扩展：Step 2 在 Step 1 的选择器基础上新增：

| 选择器 | 含义 | Step 1 | Step 2 |
| --- | --- | --- | --- |
| `all` | 所有对象 | 启用 | 启用 |
| `center_object` | bbox 中心最接近画布中心的对象 | 启用 | 启用 |
| `smallest_object` | 面积最小对象 | 启用 | 启用 |
| `rare_color_object` | dominant_color 出现频次最低的对象 | 启用 | 启用 |
| `largest_object` | 面积最大对象 | 禁用 | **启用** |
| `foreground_objects` | bg_fg 分割中的前景对象集 | 禁用 | **启用** |
| `noise_objects` | 面积或颜色频次异常低的对象集 | 禁用 | **启用** |
| `boundary_adjacent` | 与画布边界邻接的对象 | 禁用 | **启用** |

### 2.5 DSL 子集

Step 2 在 Step 1 的 DSL 子集基础上扩展，以容纳新原语和新模式：

```text
Program_step2   ::= Transform | Transform ";" Transform | Transform ";" Transform ";" Transform
Transform       ::= PrimitiveOp Args
                  | "copy" ";" FocusBlock

FocusBlock      ::= FocusClause
                  | FocusClause ";" FocusClause

FocusClause     ::= "on_copy:" Transform
                  | "on_original:" Transform

PrimitiveOp     ::= "translate" | "rotate" | "flip" | "delete" | "recolor" | "fill" | "crop"
                  | "extend_to_boundary"
                  | "merge"   -- 仅在按需启用时
```

Step 2 相对 Step 1 的 DSL 变更：

1. **最大组合深度从 2 步扩展到 3 步**：部分新概念组（如 CleanUp）可能需要"先删除噪声对象，再 crop 到剩余主体"两步串联，加上可能的尺寸规则切换，需要 3 步。
2. **新增 `extend_to_boundary` 原语**：`extend_to_boundary[target=X, direction=D]`，其中 `direction ∈ {up, down, left, right, nearest_boundary}`。
3. **按需新增 `merge` 原语**：`merge[target=X]`，将选中的多个对象合并为单一对象。

Step 1 中的受限 mode（`delete[mode=input_center_component]`、`translate[mode=rare_color_motif_to_largest_component_center]`）在 Step 2 中继续有效，且不鼓励新增更多受限 mode——Step 2 应优先通过改善分割质量和选择器泛化来解决 Step 1 遗留问题，而不是继续补 ad-hoc mode。

Step 2 明确不实现：ForEach、If、group_by、partition、construct_grid、tile、conditional_map。

## 3. Step 2 最小接口字段清单

Step 2 接口结构沿用 Step 1，仅扩展允许值域。以下只列出有变更的部分。

### 3.1 Layer 1 输出

```text
SegmentationPlan = {
  plan_id: str,
  method: "cc4" | "cc8" | "whole_grid" | "bg_fg" | "nested",    -- Step 2 扩展
  objects: [Object],
  relations: [(ObjectID, ObjectID, Relation)],
}
```

`bg_fg` 方案下的对象构建规则：

1. 统计输入网格上所有颜色的频率，取频率最高的颜色为候选背景色 `bg_color`。
2. 将所有非 `bg_color` 像素按 4-连通分量提取为前景对象。
3. 输出的 `Object.attrs` 不新增必须字段；`bg_color` 作为方案级元数据记录在 `SegmentationPlan` 的调试输出中。

`nested` 方案下的对象构建规则（若启用）：

1. 先按 cc4 提取顶层连通分量。
2. 对每个顶层分量，在其 bbox 内递归按 cc4 提取二级子分量。
3. 顶层分量和子分量都作为独立 `Object` 输出，通过 `Object.id` 的层级编码（如 `"nested:0"` 与 `"nested:0:1"`）保持父子关系。

关系扩展：

Step 2 的 `relations` 新增两类：

| 关系类型 | 格式 | 说明 |
| --- | --- | --- |
| adjacency | (obj_a, obj_b, "adjacency") | 两对象是否共享至少一个 4-邻域像素 |
| containment | (obj_a, obj_b, "containment") | obj_a 的 bbox 完全落在 obj_b 的 bbox 内 |

Step 1 已有的 `relative_position` 和 `alignment` 关系继续保留。

### 3.2 Layer 2 对齐输出

结构不变，沿用 Step 1 附录 §3.2。`merge_groups` 与 `split_groups` 在 Step 2 中仍恒为空列表。

### 3.3 Layer 2 候选集输出

结构不变，沿用 Step 1 附录 §3.3。`CandidateTransform.program` 允许引用 Step 2 新增的原语和参数。

### 3.4 Layer 3 假设输出

结构不变，沿用 Step 1 附录 §3.4。

### 3.5 Layer 5 最小归因输出

结构沿用 Step 1 附录 §3.5，新增一个可选字段：

```text
Attribution = {
  ...                              -- Step 1 全部字段保留
  concept_group: str | null,       -- Step 2 新增：当前任务所属概念组名称
}
```

`concept_group` 用于 Step 2 的概念组级聚合统计。对 Step 2a 的 Copy/Center 任务，其值为 `"Copy"` 或 `"Center"`。

## 4. Step 2 对齐白名单

Step 2 沿用 Step 1 的一对一对齐方法与回退规则，无变更：

| 方法 | Step 2 状态 | 说明 |
| --- | --- | --- |
| 像素重合匹配 | 启用 | |
| 颜色+形状匹配 | 启用 | |
| 最优二部匹配 | 启用 | |
| 合并检测 | 禁用（推迟到 Step 3） | |
| 拆分检测 | 禁用（推迟到 Step 3） | |

对齐失败回退规则与 Step 1 相同（Step 1 附录 §4）。

补充：`bg_fg` 分割方案下，对齐在前景对象集上执行（背景色像素不参与对象对齐）。这不改变对齐本身的一对一约束，只改变参与对齐的对象集合。

## 5. Step 2 最小约束与输出尺寸推断

### 5.1 允许的约束类型

Step 2 在 Step 1 的约束基础上按需新增局部一致性与计数守恒：

| 约束类型 | Step 1 状态 | Step 2 状态 | 说明 |
| --- | --- | --- | --- |
| 输出尺寸约束 | 启用 | 启用 | 仍为有限四类尺寸规则 |
| 颜色映射一致性 | 启用 | 启用 | |
| 相对位置约束 | 启用 | 启用 | |
| 局部一致性 | 禁用 | **按需启用** | 对象在变换前后保持局部形状/颜色不变 |
| 计数守恒 | 禁用 | **按需启用** | 输入/输出中特定类型对象的数量关系 |
| 全局单调性 | 禁用 | 禁用（推迟到 Step 3） | |

局部一致性按需启用理由：MoveToBoundary 任务要求对象在移动后形状和颜色不变；有了局部一致性约束，可在候选评分中排除那些破坏对象形状的错误假设。

计数守恒按需启用理由：CleanUp 任务中可能存在"输出对象数 = 输入对象数 - 噪声对象数"的守恒关系；ExtractObjects 可能存在"输出为 1 个提取对象"的守恒约束。

### 5.2 输出尺寸推断范围

Step 2 仍使用 Step 1 的四种输出尺寸规则，不新增尺寸规则类型：

1. `preserve_input_size`：输出尺寸 = 输入尺寸。
2. `fit_transformed_extent`：输出尺寸 = 执行后所有对象像素并集的最小外接矩形。
3. `crop_selected_bbox`：输出尺寸 = 被选中目标对象的 bbox。
4. `crop_center_cell`：输出尺寸 = 1×1。

各概念组的预期输出尺寸规则使用情况（基于训练数据分析）：

| 概念组 | 主要输出尺寸规则 | 说明 |
| --- | --- | --- |
| Copy（Step 2a） | preserve_input_size / fit_transformed_extent | 沿用 Step 1 |
| Center（Step 2a） | preserve_input_size / crop_selected_bbox / crop_center_cell | 沿用 Step 1 |
| MoveToBoundary | preserve_input_size | 所有训练任务输出 = 输入尺寸 |
| ExtendToBoundary | preserve_input_size | 所有训练任务输出 = 输入尺寸 |
| ExtractObjects | **crop_selected_bbox** | 所有训练任务输出小于输入（裁到主体对象 bbox） |
| CleanUp | preserve_input_size / crop_selected_bbox | 混合模式：部分保持尺寸，部分裁到清理后主体 |

`crop_selected_bbox` 在 Step 2 中的语义增强：

Step 1 中 `crop_selected_bbox` 主要用于 Center3 一类"裁到中心对象"的场景，选择标准是 `center_object`。Step 2 需要扩展其选择标准以覆盖 ExtractObjects：

- ExtractObjects 的目标对象通常是"面积最大的前景连通分量"或"最显著的非噪声对象"，选择标准为 `largest_object` 或 `foreground_objects` 中面积最大者。
- CleanUp 中使用 `crop_selected_bbox` 时，目标对象是"清理噪声后剩余的主体结构"。

这不改变 `crop_selected_bbox` 的底层语义（"输出画布 = 选中对象的 bbox"），只增加了与之配合的选择器种类。

### 5.3 强弱约束约定

沿用 Step 1 附录 §5.3 的保守策略，无变更。

## 6. Step 2 运行遥测字段表

Step 2 沿用 Step 1 的遥测字段（Step 1 附录 §6），新增以下内容：

1. `concept_group`：当前任务所属概念组名称。
2. 概念组级聚合统计：在批量运行报告中，按概念组分组统计精确求解数、失败类型分布和平均耗时。

BEAM_SIZE 设置：Step 2 初始沿用 `STEP2_BEAM_SIZE = 64`（与 Step 1 终态相同）。若实现阶段发现新概念组的候选空间显著大于 Copy/Center，允许上调，但须在代码和文档中显式记录变更及理由。

pre_priority 代理特征：Step 2 沿用 Step 1 的 `attr_ref_ratio` 和 `ast_depth` 两个字符串级代理，并延续 Step 1 终态的两项修正（排除 copy block 结构分隔符计入 ast_depth、将符号参数计入 attr_ref）。若需新增代理特征，须在实验报告中记录。

## 7. Step 2 明确不做的能力

以下能力在 Step 2 中一律视为禁用。与 Step 1 相比，已从禁用列表中移除的项用 ~~删除线~~ 标记：

1. 排序模型训练与推理。
2. 知识状态写回、扩展准入、三阶段知识重写。
3. merge / split / partition（merge 仅在按需启用后移出本列表）。
4. ~~bg_fg 分割策略~~（已在 Step 2 启用）。
5. bbox / repeat 分割策略。
6. ~~邻接关系~~（已在 Step 2 启用）。
7. ~~包含关系~~（已在 Step 2 启用）。
8. 对称关系（推迟到 Step 3）。
9. 完整关系集与完整约束集。
10. 路径 B 约束求解。
11. 诊断任务消费。
12. 为提高成功率而加入样例级 ad-hoc 特判。
13. 未经文档显式登记、却以"通用能力"名义混入 Step 2 的任务族级受限 mode。

相对 Step 1 新增的禁用项：

14. scale 原语。
15. conditional_map 原语。
16. sort / group_by / tile / construct_grid / partition 原语。
17. ForEach / If 控制流。
18. 组合表达式、算术树或用户自定义参数名。
19. 多锚点广播、一般 repeat、可编排的多步布局规划。

## 8. 与后续 Step 的接口约定

Step 2 与 Step 1 保持以下接口兼容：

1. `alignment_id` 与 `alignment_family_id` 都不得省略。
2. `Hypothesis` 必须维持 `(plan_id, alignment_id, alignment_family_id, constraint_subset, program)` 结构。
3. `Attribution` 必须保留 `selected_plan`、`selected_alignment`、`selected_alignment_family`、`selected_program`、`selected_constraints` 与 `search_stats`；新增的 `concept_group` 字段对 Step 1 任务仍可填充，不引入不兼容。
4. `ProgramSketch` 与 `Program` 的分层必须保留。

Step 2 代码放在 `phase1/src/step2/` 独立目录下，从 `step1/` 复制后演进。`step1/` 代码保持冻结不修改，作为可复现基线。

Step 2 → Step 3 的接口约定：

1. Step 2 的归因输出必须能区分"分割不足"（bg_fg/nested 仍不够）和"原语表达力不足"（需要 scale/conditional_map 等 Step 3 原语）。
2. Step 2 结束时必须据实报告 beam/timeout 的实际使用情况，为 Step 3 设定真实搜索预算提供依据。
3. 若 Step 2 结束后仍无法稳定区分"对齐失败"和"程序表达力不足"，则不得进入 Step 3（参见架构文档 §12.2 成功标准）。
