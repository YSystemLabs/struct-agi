# 第一阶段 Step 2 最小接口与任务清单附录

> 版本：v0.1
>
> 状态：已按 Step 2 当前终态同步（含 Step 2b 冻结边界与验收口径）
>
> 作用：为 Step 2 冻结任务边界、最小接口、对齐白名单与运行遥测，消除实现歧义。

## 1. 文档定位

本附录是 [Step1最小接口与任务清单附录-0v1.md](../step1/Step1最小接口与任务清单附录-0v1.md) 的增量版本，**只描述 Step 2 相对于 Step 1 的变更与新增**。凡本附录未提及的部分，沿用 Step 1 附录的定义。

本附录引用的算法设计来源为 [第一阶段算法架构-0v4.md](../第一阶段算法架构-0v4.md)，特别是 §3.3（分割策略）、§3.4（关系提取）、§4.2.1（原语集）、§4.3（输出尺寸推断）和 §12.2（Step 2 计划）。

Step 2 分两个子阶段：

- **Step 2a**：在 Step 1 冻结的 Copy/Center 数据上，利用新放开的能力修复 Step 1 遗留失败（目标 ≥9/12）。
- **Step 2b**：将求解器扩展到 4 个新概念组：MoveToBoundary、ExtendToBoundary、ExtractObjects、CleanUp。

截至 2026-04-05，Step 2a 的项目结论已更新为：**8/12，按“有条件通过”验收**。这意味着项目状态上允许进入 Step 2b 实施，但同时明确：Copy3-6 暴露出的边界外能力缺口不回流 Step 2b 修复，而是登记为 Step 3 提前引入能力。

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
| merge | 禁用 | 禁用（推迟到 Step 3） | Step 1-2 只支持一对一对象映射，Layer 2/3 无合法对齐语义支撑 merge |
| sort | 禁用 | 禁用（推迟到 Step 3） | |
| group_by | 禁用 | 禁用（推迟到 Step 3） | |
| tile | 禁用 | 禁用（推迟到 Step 3） | |
| construct_grid | 禁用 | 禁用（推迟到 Step 3） | |
| partition | 禁用 | 禁用（推迟到 Step 3） | |

`extend_to_boundary` 启用理由：架构文档 §4.2.1 定义其签名在 Step 2 中细化为 `Object × SourceSpec × DirectionSpec → Object`，语义为"从对象的封闭白名单子边界出发，沿指定方向或封闭白名单的参数化方向延伸对象，直到触及画布边界或另一个对象边界"。这是 ExtendToBoundary 概念组的核心操作，无法用现有原语组合表达。

补充边界：Step 2 中的 `SourceSpec` 与 `DirectionSpec` 都是单假设级别的固定参数，不包含“按 pair 几何关系动态选方向/轴”的条件化语义。ETB1 的分析结果表明，它存在统一几何规律，但该规律要求在不同 pair 上切换 `center_row/right` 与 `center_col/down`；因此 ETB1 应登记为 7B overflow，而不是视为 beam 或打分缺陷。

补充说明：ETB4 若要继续留在 7B 内，只允许通过新增封闭 target selector `gap_thinner_object` 处理 relation-conditioned target selection，不允许继续扩展 `SourceSpec` / `DirectionSpec`。该 selector 只覆盖“两对象、单轴 gap”布局，用于在现有 `to_nearest_object_boundary` 语义下稳定选中应被延伸的那一方。

补充说明：ETB5 已分析确认为更强的 7B overflow。它需要的是对角/放射式扩张，而不是当前白名单中的轴向 `extend_to_boundary`。当前候选池分析显示 ETB5 的 `extend_to_boundary` 假设数为 0，说明问题不是 beam 存活，而是当前 7B 语义家族根本未覆盖该任务。

补充说明：ETB6 也应归入同类 7B overflow。其输出规律是沿对角方向把稀疏像素延伸到边界，当前 `DirectionSpec` 并不支持该类方向；因此即使调试中出现 `106 -> 64` 的 beam 饱和，问题本质仍然不是 keepalive 可修复的家族存活问题，而是 Layer 2 根本不会生成 `extend_to_boundary` 候选。

阶段判断补充：在当前冻结的 7B 语义边界下，ExtendToBoundary 的现实上界应明确记为 **2/6**，即 ETB2 与 ETB4；ETB1、ETB3、ETB5、ETB6 应整体转记为 Step 3 能力缺口，而不是继续留在 Step 2b 作为待调参残差。

Step 3 能力缺口总结：ETB1 缺的是按 pair 几何关系条件化选择 `source/direction` 的能力；ETB3 缺的是超出轴向白名单的对角/构造式传播；ETB5、ETB6 缺的是对角或放射式边界延伸。四者共同要求的是更高一层的几何条件化扩张语义，而不是继续给 `extend_to_boundary` 增补少量局部 token。

`merge` 禁用理由：架构文档明确 Step 1-2 只支持一对一对象映射（`merge_groups` 和 `split_groups` 为空）。merge 需要 Layer 2 的合并检测、Layer 3 的多对一对齐语义来支撑，这些从 Step 3 起才逐步支持。即使 CleanUp 涉及碎片合并需求，Step 2 也应通过 `delete[target=noise_objects]` 配合 `crop_selected_bbox` 间接实现，而不是引入无对齐语义支撑的 merge 原语。

补充说明：虽然 Copy3-6 的 Step 2a 终态已经把部分后续需求明确指向 `anchor-relative` 参数化位移、`repeat`、`tile`、`construct_grid` 一类能力，但这些能力在项目记录口径上**不属于 Step 2b 扩边界实现内容**，而是登记为 Step 3 提前引入能力。

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

`extend_to_boundary` 的 `source` 与 `direction` 参数在 Step 2 都采用封闭白名单，不是开放表达式：

| 参数 | 含义 | Step 1 | Step 2 |
| --- | --- | --- | --- |
| `full_boundary` | 使用对象全部像素作为 source 集合，再按方向选前沿 | 禁用 | **启用** |
| `top_edge` / `bottom_edge` / `left_edge` / `right_edge` | 只从 bbox 对应边上的像素出发 | 禁用 | **启用** |
| `center_row` | 只从 bbox 中心最近行出发；偶数高度并列时取较小行号 | 禁用 | **启用** |
| `center_col` | 只从 bbox 中心最近列出发；偶数宽度并列时取较小列号 | 禁用 | **启用** |

| 参数 | 含义 | Step 1 | Step 2 |
| --- | --- | --- | --- |
| `up` / `down` / `left` / `right` | 固定单方向延伸 | 禁用 | **启用** |
| `nearest_boundary` | 朝最近画布边界延伸；等距时按 `up > down > left > right` | 禁用 | **启用** |
| `to_nearest_object_boundary` | 朝最近对象的最近边界方向延伸；并列时优先正交投影重叠，再按对象 id，再按 `up > down > left > right` | 禁用 | **启用** |
| `horizontal_both` | 同时向左、向右双向延伸，两侧独立停止 | 禁用 | **启用** |
| `vertical_both` | 同时向上、向下双向延伸，两侧独立停止 | 禁用 | **启用** |

Step 2 明确不放开 diagonal、radial、flood-fill 式方向参数，也不允许按样例动态拼接新的 `direction` token` 或任意 source mask。

目标选择器扩展：Step 2 在 Step 1 的选择器基础上新增。选择器分为两类，返回类型在接口中显式声明：

**单对象选择器**（返回恰好 1 个对象）：

| 选择器 | 含义 | Step 1 | Step 2 |
| --- | --- | --- | --- |
| `center_object` | bbox 中心最接近画布中心的对象 | 启用 | 启用 |
| `smallest_object` | 面积最小对象 | 启用 | 启用 |
| `rare_color_object` | dominant_color 出现频次最低的对象 | 启用 | 启用 |
| `largest_object` | 面积最大对象 | 禁用 | **启用** |
| `gap_thinner_object` | 在“两对象、单轴 gap”布局中，返回沿 gap 轴更细的那一方；纵向 gap 比较 width，横向 gap 比较 height | 禁用 | **启用（仅 ETB4 类 ExtendToBoundary）** |

单对象选择器 tie-break 规则（延续 Step 1 级别的固定 tie-break 纪律）：
- `largest_object`：面积并列时，取 `Object.id` 字典序最小的对象。
- `smallest_object`：同上，取 `Object.id` 字典序最小。
- `center_object`：距离并列时，取 `Object.id` 字典序最小。
- `rare_color_object`：频次并列时，取 `Object.id` 字典序最小。
- `gap_thinner_object`：仅在存在可识别的“两对象、单轴 gap”对时生效；若为纵向 gap，则取 width 更小者，若 width 并列则取 area 更小者，再按 `Object.id`；若为横向 gap，则改为比较 height，再按 area、`Object.id`。若当前 plan 不满足该布局，则该选择器返回空。

**对象集选择器**（返回 0~N 个对象的集合）：

| 选择器 | 含义 | Step 1 | Step 2 |
| --- | --- | --- | --- |
| `all` | 所有对象 | 启用 | 启用 |
| `foreground_objects` | bg_fg 分割中的全部前景对象 | 禁用 | **启用** |
| `noise_objects` | 面积严格小于当前 plan 中所有对象面积中位数的 1/4 的对象（Step 2 临时固定启发式，见备注） | 禁用 | **启用** |
| `boundary_adjacent` | bbox 任意一边与画布边界接触（距离=0）的全部对象 | 禁用 | **启用** |

> **noise_objects 阈值备注**：“面积 < 中位数 × 1/4”仍只应被视为 Step 2 的临时固定启发式，而不应再被当作已验证充分的 CleanUp 语义。2026-04-06 的 7D 基线诊断已经表明：在多个 CleanUp 训练任务中，bg_fg plan 会出现“大量单像素对象并存”或“主体碎片与噪声都很小”的情况，此时该阈值经常返回空集或不稳定选择。实现时仍必须在调试输出中记录：（1）当前 plan 的对象面积分布，（2）中位数值，（3）触发的 noise_objects 数量；同时要把 7D 当前结论写清楚：该 token 已纳入接口白名单，但现有阈值尚不足以支撑 CleanUp 收口。

**类型约束**：每个原语的 `target` 参数声明其接受的选择器类型。接受单对象选择器的原语（如 `translate`、`copy`、`extend_to_boundary`）不能直接接受对象集选择器；接受对象集选择器的原语（如 `delete`、`recolor`）可同时接受单对象选择器（等价于单元素集合）。若需从对象集中选出单个对象，应使用对应的单对象选择器（如 `largest_object` 而非 "foreground_objects 中面积最大者"），不在 DSL 中引入二次归约语义。

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
```

Step 2 相对 Step 1 的 DSL 变更：

1. **最大组合深度从 2 步扩展到 3 步**：部分新概念组（如 CleanUp）可能需要"先删除噪声对象，再 crop 到剩余主体"两步串联，加上可能的尺寸规则切换，需要 3 步。
2. **新增 `extend_to_boundary` 原语**：`extend_to_boundary[target=X, source=S, direction=P]`，其中 `source` 允许 `full_boundary / top_edge / bottom_edge / left_edge / right_edge / center_row / center_col`，`direction` 允许 `up / down / left / right / nearest_boundary / to_nearest_object_boundary / horizontal_both / vertical_both`。

Step 1 中的受限 mode（`delete[mode=input_center_component]`、`translate[mode=rare_color_motif_to_largest_component_center]`）在 Step 2 中继续有效，且不鼓励新增更多受限 mode——Step 2 应优先通过改善分割质量和选择器泛化来解决 Step 1 遗留问题，而不是继续补 ad-hoc mode。

Step 2 明确不实现：ForEach、If、group_by、partition、construct_grid、tile、conditional_map，以及 diagonal / radial 一类开放式方向扩张与任意掩码式 source 选择。

## 3. Step 2 最小接口字段清单

Step 2 接口结构沿用 Step 1，仅扩展允许值域。以下只列出有变更的部分。

### 3.1 Layer 1 输出

```text
SegmentationPlan = {
  plan_id: str,
  method: "cc4" | "cc8" | "whole_grid" | "bg_fg" | "nested",    -- Step 2 扩展
  objects: [Object],
  relations: [(ObjectID, ObjectID, Relation)],
  bg_color: int | None,    -- bg_fg 方案下为识别的背景色，其他方案下为 None（默认 0）
}
```

`bg_fg` 方案下的对象构建规则：

1. 统计输入网格上所有颜色的频率，取频率最高的颜色为候选背景色 `bg_color`。若多种颜色并列最高频，按颜色数值升序取最小值（固定 tie-break，与 Step 1 对 cc4 背景色=0 的默认值一致）。
2. 将所有非 `bg_color` 像素按 4-连通分量提取为前景对象。
3. 输出的 `Object.attrs` 不新增必须字段；`bg_color` 作为 `SegmentationPlan` 的正式字段存储（`bg_color: int | None`），供 Layer 4 渲染时使用。非 bg_fg 方案的 `bg_color` 保持 `None`（等价于默认值 0）。

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

- ExtractObjects 的目标对象通常是"面积最大的前景连通分量"或"最显著的非噪声对象"，选择标准为单对象选择器 `largest_object`（在 bg_fg 分割方案下，`largest_object` 自然指向面积最大的前景对象）。
- CleanUp 中使用 `crop_selected_bbox` 时，目标对象是"清理噪声后剩余的主体结构"。

当前 7C 的阶段验证已经表明：仅靠 `largest_object` 与 `crop_selected_bbox` 的现有组合，就足以让 ExtractObjects 达到 **2/6** 的最低精确门槛（当前 exact pass 为 ExtractObjects1、ExtractObjects3）。因此，`noise_objects` 在 7C 中仍保留为合法选择器和允许模板，但当前最小验收并不依赖显式 `delete[target=noise_objects] ; crop[...]` 链路才能成立。

相对地，当前 7D 的阶段验证已经表明：即使直接手工执行 `delete[target=noise_objects]` 或 `delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]`，在现有 executor 语义下也仍然是 **0/6**。问题不只在输出尺寸规则，而在于当前系统缺少“删除噪声后恢复结构化背景/主体局部纹理”的局部修复语义。因此，`crop_selected_bbox` 对 CleanUp 仍然只是允许模式，不代表 7D 已具备可收口实现。

若后续在 Step 2 中尝试补入这一类修复语义，接口边界必须固定如下：只允许依赖局部上下文一致性，不允许依赖任务名、颜色特判、图样类别特判，也不允许按 train pair 或样例外观切换规则。任何需要这些额外条件的信息，都应被视为 Step 3 的条件化结构语义，而不是 Step 2 的合法扩展。

同样需要固定记录当前实验结论：在这条接口边界下，受限原型目前只得到 **1/6** exact（仅 CleanUp2），因此它只能被视为“局部一致性语义存在弱信号”的证据，不能被当作可直接并入 Step 2 executor 的已验证接口能力。

这不改变 `crop_selected_bbox` 的底层语义（"输出画布 = 选中对象的 bbox"），只增加了与之配合的选择器种类。

### 5.3 强弱约束约定

沿用 Step 1 附录 §5.3 的保守策略，无变更。

## 6. Step 2 运行遥测字段表

Step 2 沿用 Step 1 的遥测字段（Step 1 附录 §6），新增以下内容：

1. `concept_group`：当前任务所属概念组名称。
2. 概念组级聚合统计：在批量运行报告中，按概念组分组统计精确求解数、失败类型分布和平均耗时。
3. `bg_color` 诊断：凡使用 `bg_fg` 分割的 plan，调试输出中必须记录识别出的 `bg_color`。
4. `regression_flags`：批量运行报告中必须显式标记相对 Step 1 基线和相对前序概念组引入阶段的回归任务。
5. `noise_objects` 诊断：凡使用 `noise_objects` 选择器的任务，调试输出中必须记录当前 plan 的对象面积分布、中位数值和触发的 noise_objects 数量。

BEAM_SIZE 设置：Step 2 初始沿用 `STEP2_BEAM_SIZE = 64`（与 Step 1 终态相同）。若实现阶段发现新概念组的候选空间显著大于 Copy/Center，允许上调，但须在代码和文档中显式记录变更及理由。

对 Step 2b 的 ExtendToBoundary 允许一条局部 keepalive 例外：当 beam 已饱和且 top-`STEP2_BEAM_SIZE` 中不存在任何 `extend_to_boundary` 假设，但排序靠后的候选中存在 `extend_to_boundary` 时，允许额外追加 1 个 `extend_to_boundary` keepalive 槽位进入评估。该例外仅用于避免正确原语家族在截断前整体缺席；不得通过修改全局 `pre_priority` 或扩大 keepalive 数量来间接改变其他概念组的搜索分布。

pre_priority 代理特征：Step 2 沿用 Step 1 的 `attr_ref_ratio` 和 `ast_depth` 两个字符串级代理，并延续 Step 1 终态的两项修正（排除 copy block 结构分隔符计入 ast_depth、将符号参数计入 attr_ref）。若需新增代理特征，须在实验报告中记录。

## 7. Step 2 明确不做的能力

以下能力在 Step 2 中一律视为禁用。与 Step 1 相比，已从禁用列表中移除的项用 ~~删除线~~ 标记：

1. 排序模型训练与推理。
2. 知识状态写回、扩展准入、三阶段知识重写。
3. merge / split / partition。
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

其中，已在 Step 2a 终态中被明确登记为 Step 3 提前引入能力的条目包括：

1. Copy3 / Copy4 所需的参数化 anchor-relative 位移语义。
2. Copy5 / Copy6 所需的 repeat / tile / construct_grid 一类构造语义。

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
3. Step 2 完成的最低归因要求是区分"分割不足"与"原语表达力不足"；但若 Step 2 结束后仍无法稳定区分"对齐失败"和"程序表达力不足"，则不得进入 Step 3（参见架构文档 §12.2 成功标准）。
4. Step 2a 若以“有条件通过”状态放行 Step 2b，则必须同步给出“哪些能力不回流 Step 2b、而登记为 Step 3 提前引入能力”的明确列表，避免 Step 2b 实施阶段发生边界漂移。
5. 当前已登记的 Step 3 提前引入能力为：
  - Copy3 / Copy4 → 参数化 anchor-relative 位移语义
  - Copy5 / Copy6 → repeat / tile / construct_grid 一类构造语义
