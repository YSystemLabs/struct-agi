# 第一阶段 Step 2 实现设计

> 版本：v0.1
>
> 状态：Step 2 已实施到 Step 2b 验收阶段（Step 2a 为 8/12、有条件通过；Step 2b 已验收；整体未最终收口）
>
> 作用：定义 Step 2 的实现顺序、各层变更设计、测试策略与验收门槛。

## 1. 文档定位

本文档是 Step 2 的实现设计正文，只回答"怎么实现 Step 2"。

本文档不重新定义 Step 2 的任务范围、最小接口和冻结边界。这些内容以 [Step2最小接口与任务清单附录-0v1.md](Step2最小接口与任务清单附录-0v1.md) 为准。

本文档与以下文档的关系如下：

| 文档 | 作用 |
| --- | --- |
| [第一阶段研究计划-0v1.md](../第一阶段研究计划-0v1.md) | 定义研究问题、成功标准与退出条件 |
| [第一阶段算法架构-0v4.md](../第一阶段算法架构-0v4.md) | 定义完整五层架构与长期接口 |
| [Step2最小接口与任务清单附录-0v1.md](Step2最小接口与任务清单附录-0v1.md) | 冻结 Step 2 的实现边界 |
| [Step1实现设计-0v1.md](../step1/Step1实现设计-0v1.md) | Step 1 冻结基线（本文档的前置版本） |
| 本文档 | 规定 Step 2 的实现顺序、各层变更、测试与验收 |

## 2. Step 2 实现目标

Step 2 分两个子阶段，目标分别如下。

### 2.1 Step 2a：修复 Copy/Center 遗留失败

在 Step 1 冻结的 12 个训练任务上，利用 Step 2 新放开的能力（bg_fg 分割、邻接/包含关系、扩展选择器），将精确求解数从 **6/12 提升到 ≥9/12**。

Step 2a 不引入新概念组数据，只使用 Copy1-6 与 Center1-6。

### 2.2 Step 2b：扩展到 4 个新概念组

在 MoveToBoundary1-6、ExtendToBoundary1-6、ExtractObjects1-6、CleanUp1-6 共 24 个新训练任务上，建立初始求解能力。

Step 2b 的验收标准见 §14。

### 2.3 Step 2 不追求

1. 覆盖 ConceptARC 全部 16 个概念组。
2. 引入排序模型、知识状态写回或三阶段知识重写。
3. 在 ARC-AGI-2 上报告主结果。
4. 通过样例级特判堆出成功率。
5. 消费诊断任务。

## 3. 边界约束

### 3.1 代码组织

Step 2 代码放在 `phase1/src/step2/` 独立目录下，从 `step1/` 复制后演进。`phase1/src/step1/` 保持冻结不修改，作为可复现基线。

推荐目录结构：

```text
phase1/
├── src/
│   ├── step1/                        # 冻结，不修改
│   └── step2/
│       ├── __init__.py
│       ├── config.py                 # Step 2 配置（扩展白名单、新任务清单）
│       ├── data/
│       │   ├── __init__.py
│       │   ├── loader.py             # 扩展：加载 6 个概念组
│       │   └── models.py             # 沿用，必要时扩展
│       ├── layer1/
│       │   ├── __init__.py
│       │   ├── perception.py         # 新增 bg_fg（和可选 nested）分割
│       │   ├── objects.py            # 沿用
│       │   └── relations.py          # 新增 adjacency / containment
│       ├── layer2/
│       │   ├── __init__.py
│       │   ├── alignment.py          # 适配 bg_fg 分割输出
│       │   ├── diff.py               # 新增 extend_to_boundary 差异类型
│       │   ├── constraints.py        # 按需新增局部一致性 / 计数守恒
│       │   └── sketches.py           # 扩展：新原语候选模板
│       ├── layer3/
│       │   ├── __init__.py
│       │   ├── hypothesis.py         # 沿用
│       │   ├── scoring.py            # 适配新原语的描述长度计算
│       │   └── selector.py           # 沿用
│       ├── layer4/
│       │   ├── __init__.py
│       │   ├── dsl.py                # 新增 extend_to_boundary 解析
│       │   ├── executor.py           # 新增原语执行逻辑
│       │   └── render.py             # 修复 bg_color 硬编码
│       ├── layer5/
│       │   ├── __init__.py
│       │   ├── verify.py             # 沿用
│       │   └── attribution.py        # 新增 concept_group 字段
│       ├── runner/
│       │   ├── __init__.py
│       │   ├── task_runner.py        # 沿用
│       │   └── batch_runner.py       # 扩展：6 组批量运行
│       └── utils/                    # 沿用
└── outputs/
    └── step2/
        ├── debug/
        └── reports/
```

### 3.2 实现原则

沿用 Step 1 的四条实现原则（可审计优先、单层先稳定、主干先做、遥测同步），新增一条：

5. **不回归 Step 1 基线**。每一轮 Step 2 变更后，必须验证 Step 1 的 6/12 基线不退化。若 Step 2 代码在 Copy/Center 上的精确求解数低于 6，视为回归，须先修复再继续。

## 4. Step 2a 失败根因分析

Step 1 终态 6/12，6 个失败任务均归因为 `ABSTRACTION_FAIL`。

**关键前提**：Step 1 实验报告的冻结结论明确指出，当前失败样式主要指向“更强对象表示、对象组复制、repeat/tile、层级/包含”等能力缺口。其中，Step 2 仅放开更强对象表示（bg_fg 分割、层级/包含关系）；对象组复制和 repeat/tile **不在 Step 2 边界内**，从 Step 3 起才逐步支持。因此 Step 2 的任务是重新诊断每个失败任务，诚实区分 Step 2 可修复的部分与需要登记为 Step 3 提前引入能力的部分。

### 4.1 Copy2（像素准确率 96.4%，ABSTRACTION_FAIL）

**选中程序**：`copy[target=smallest_object] ; on_copy: translate[...dx=to_largest_object_center_dx,...] ; on_original:`

**Step 1 冻结诊断**：ABSTRACTION_FAIL——对象表示和选择器泛化不足。`smallest_object` 在不同 train pair 中指代不一致（有时是源图样，有时是噪声碎片），导致选择器跨 pair 不稳定。

**Step 2 可干预范围**：
1. `bg_fg` 分割可把噪声碎片归入背景，使前景对象集更干净，`smallest_object` 选中的对象可能更稳定。
2. 在 bg_fg 方案下补充 `largest_object` 候选，与 `smallest_object` 并列参与评估，而不是预设哪个选择器一定正确。bg_fg 分割后前景对象集变小，两个选择器的指向可能变得更一致。

**诚实预期**：若该任务的真实变换仅涉及单对象搬运且 bg_fg 能消除噪声干扰，修复概率较高。若涉及对象组复制或 repeat 模式，则超出 Step 2 表达力。

> **Step 2a 实施结果（2026-04-05）**：✅ **已修复，100% 精确求解**。
>
> 根因不是 bg_fg 或选择器——cc4 下原始程序 `copy[target=smallest_object] ; on_copy: translate[target=all,dx=to_largest_object_center_dx,dy=to_largest_object_center_dy] ; on_original:` 在 train pairs 上的逻辑是正确的，但渲染层 (`render_objects`) 只使用对象的单一 `color` 属性着色，导致多色连通对象（如 Copy2 的 3×3 图样含颜色 2 和 4）在渲染时丢失内部颜色结构。
>
> 修复方式：在 `ObjectData` 中新增 `pixel_colors: dict[Cell, int]` 字段，在 Layer 1 构建对象时记录每像素原始颜色，并在所有 Layer 4 变换（translate、rotate、flip、recolor、fill、crop 等）中完整传播 `pixel_colors`。`render_objects` 改为按 `pixel_colors` 着色，仅在无 `pixel_colors` 时回退到单色。
>
> 此修复是通用基础设施改进，不是任务级特判。

### 4.2 Copy3（像素准确率 89.4%，ABSTRACTION_FAIL，beam_saturated）

**选中程序**：`delete[target=all,mode=input_center_component]`

**Step 1 冻结诊断**：ABSTRACTION_FAIL。系统选中 delete 而非 copy，beam 饱和（184 候选 → 64 评估）是二级症状。

**Step 2 可干预范围**：
1. 改善 `pre_priority` 预排序，使 copy 类候选不被 delete 类候选压制。
2. 上调 BEAM_SIZE 减少截断。

**诚实预期**：beam 调整和 pre_priority 改善只能解决"正确候选存在于搜索空间但被截断"的情况。若该任务的真实变换涉及对象组复制或 repeat/tile（Step 1 报告标注的能力缺口），则搜索空间中根本不存在正确候选，beam 调整无法修复。此任务的修复信心**低**。

> **Step 2a 实施结果（2026-04-05）**：❌ **未修复，93.7%**（Step 1 为 89.4%，有小幅提升但未精确求解）。
>
> 穷举验证确认：Copy3 的两个 train pair 需要不同的位移量（pair 0 需 dx=7, pair 1 需 dx=6,dy=3），且 pair 1 即使使用最优常数位移也只能达到 99.5%，因为真实变换是"相对于锚点对象的参数化位移"——不同 pair 中锚点间距不同，导致常数位移无法跨 pair 泛化。此模式属于 Step 3 的参数化 anchor-relative 语义，超出 Step 2 DSL 表达力。
>
> 与设计预期一致：修复信心低，记为 Step 3 提前引入能力。

### 4.3 Copy4（像素准确率 82.6%，ABSTRACTION_FAIL，beam_saturated）

**选中程序**：`delete[target=cc4:5]`

**Step 1 冻结诊断**：同 Copy3，ABSTRACTION_FAIL + beam 饱和。

**诚实预期**：同 Copy3，修复信心**低**。

> **Step 2a 实施结果（2026-04-05）**：❌ **未修复，83.7%**（与 Step 1 持平）。
>
> 穷举验证确认：Copy4 同样需要 pair-dependent 位移量，属于参数化 anchor-relative 语义。与 Copy3 根因相同，记为 Step 3 提前引入能力。

### 4.4 Copy5（像素准确率 38.0%，ABSTRACTION_FAIL）

**选中程序**：`crop[target=cc4:0,mode=tight_bbox]`

**Step 1 冻结诊断**：ABSTRACTION_FAIL。crop 操作本身不足以表达该任务的真实变换规则，38% 的低像素准确率说明偏差不是微调问题。

**Step 2 可干预范围**：
1. `bg_fg` 分割提供更好的前景/背景分离。
2. 补充 `largest_object` 候选，与 `smallest_object` 并列参与评估，由 Layer 3 的评分决定哪个更优。

**诚实预期**：若任务涉及块级重复、构造性变换或 repeat/tile，超出 Step 2 表达力范围。修复信心**低**，大概率仍归因为 ABSTRACTION_FAIL 并记录为 Step 3 候选。

> **Step 2a 实施结果（2026-04-05）**：❌ **未修复，37.0%**（与 Step 1 持平）。
>
> Copy5 的输出网格尺寸与输入不同（如 input 4×5 → output 4×9），涉及 repeat/tile 模式。穷举常数位移的最高准确率仅 52.8%。超出 Step 2 表达力，记为 Step 3 提前引入能力。

### 4.5 Copy6（像素准确率 43.7%，ABSTRACTION_FAIL）

**选中程序**：`copy[target=smallest_object] ; on_copy: translate[...dx=to_largest_object_center_dx,...] ; on_original:`

**Step 1 冻结诊断**：ABSTRACTION_FAIL。候选只覆盖了单次搬运，该任务可能涉及多对象放置或 repeat 模式。

**Step 2 可干预范围**：同 Copy2 的 bg_fg + 新选择器方向。

**诚实预期**：若真实变换涉及多锚点放置或 repeat，Step 2 边界内无法解决。修复信心**低**，应登记为 Step 3 提前引入能力。

> **Step 2a 实施结果（2026-04-05）**：❌ **未修复，43.7%**（与 Step 1 持平）。
>
> Copy6 的输出网格尺寸与输入不同（如 input 3×11 → output 7×11），属于 repeat/tile 模式。超出 Step 2 表达力，记为 Step 3 提前引入能力。

### 4.6 Center3（像素准确率 2.1%，ABSTRACTION_FAIL）

**选中程序**：`delete[target=cc8:0]`

**Step 1 冻结诊断**：ABSTRACTION_FAIL。灾难性失败。cc4/cc8 无法把嵌套在背景中的前景主体正确分离，导致对齐和候选生成全面偏差。2.1% 的像素准确率说明错误不在候选筛选，而在感知层——这是 Step 1 报告标注的"更强对象表示、层级/包含"缺口的典型表现。

**Step 2 修复方向**：
1. **最高优先级**：`bg_fg` 分割直接解决 Center3 的核心感知问题。通过频率分析识别背景色后，前景对象可被正确分离。
2. 若 `bg_fg` 不足，启用 `nested` 分割做两级递归提取。
3. `containment` 关系帮助识别嵌套结构中的主体与容器对象。

**诚实预期**：修复信心**高**。Center3 的失败根因是感知层对象提取不足，bg_fg 直接对应这一缺口。

> **Step 2a 实施结果（2026-04-05）**：✅ **已修复，100% 精确求解**。
>
> 修复实际由三层问题的逐层解决组成：
> 1. **bg_fg 输出回退**：Center3 的 output 中主导颜色非 0，bg_fg 输出侧识别出 0 个前景对象。修复：当 bg_fg output 对象为空时，回退到 cc4 output 用于对齐。
> 2. **同色连通区域分割**：`extract_cc_objects` 原始实现将所有非零相邻像素视为同一连通分量，导致 bg_color=0 时 bg_fg 输出与 cc4 完全相同。修复：为 bg_fg 在 `extract_cc_objects` 中增加 `same_color=True` 参数，只连通同色像素。
> 3. **crop 候选 beam 存活**：正确程序 `crop[target=center_object,mode=tight_bbox]` 存在于候选集但在 beam 截断中被全部剪除（13 个 crop 候选 → 0 个存活）。修复：在 `_semantic_consistency_bonus` 中为 crop 类候选添加 +0.15 语义奖励。
>
> 最终选中程序：`crop[target=center_object,mode=tight_bbox]`（bg_fg 方案）。

### 4.7 失败分布汇总与可修复性评估

| 失败类别 | 任务 | Step 1 冻结根因 | Step 2 可干预手段 | 修复信心 | Step 2a 实施结果 |
| --- | --- | --- | --- | --- | --- |
| 对象表示不足 + 选择器不稳定 | Copy2 | 更强对象表示，可能涉及对象组复制 | bg_fg 分割 + 新选择器 | 中 | ✅ **已修复**（pixel_colors） |
| 选择器不稳定 + 多对象放置 | Copy6 | 多锚点放置或 repeat 模式 | bg_fg + 新选择器 | 低 | ❌ 未修复（43.7%，repeat/tile） |
| 表达力不足 + beam 饱和 | Copy3, Copy4 | 对象组复制、repeat/tile | pre_priority + beam 调整 | 低 | ❌ 未修复（93.7% / 83.7%，anchor-relative） |
| 表达力不足 | Copy5 | 构造性变换或 repeat/tile | bg_fg + largest_object | 低 | ❌ 未修复（37.0%，repeat/tile） |
| 感知层灾难性失败 | Center3 | 更强对象表示、层级/包含 | bg_fg（+ 可选 nested）分割 | **高** | ✅ **已修复**（bg_fg + crop） |

**关键结论（实施前）**：Step 2a 的 ≥9/12 目标中，高信心增量主要来自 Center3（bg_fg 修复）。Copy2-6 中，仅 Copy2 有中等修复信心，Copy3-6（含 Copy6）的根因大多涉及 Step 2 边界外的能力（对象组复制、repeat/tile、多锚点放置），修复信心均为低。因此，≥9/12 更应被视为进取型目标：实现路径至少需要"保住 Step 1 的 6 个 + 修复 Center3"，并再从 Copy 中争取约 2 个增量；其中除 Copy2 外，其余增量大多属于低置信尝试。若最终 Copy 改善不足，应诚实归因，而不是在 Step 2 边界内硬凑结果。

> **实施后结论（2026-04-05）**：最终 **8/12**（+2：Center3、Copy2），基线 6/12 无回退。
>
> 实施结果与设计预期高度一致：
> - 高信心目标 Center3 如期修复。
> - 中信心目标 Copy2 成功修复，但修复路径不是 bg_fg/选择器（设计预期），而是 pixel_colors 基础设施修复——说明 Step 1 的根因诊断"对象表示不足"是准确的，只是具体症状在渲染层而非感知层。
> - 低信心目标 Copy3-6 全部未修复，穷举验证确认它们分别需要 anchor-relative 参数化位移（Copy3/4）或 repeat/tile 模式（Copy5/6），均超出 Step 2 DSL 表达力。
> - ≥9/12 门槛未达到，但这是因为低信心目标确认不可修复，而不是可修复的目标被遗漏。
>
> Copy3-6 的能力缺口明确登记为 Step 3 提前引入能力：
> - Copy3/4 → 参数化 anchor-relative 位移语义
> - Copy5/6 → repeat/tile / construct_grid + 输出尺寸变化

## 5. Step 2a 各层变更设计

> **实施状态说明**：以下设计已全部在 Step 2a 实施中落地，但实际修复路径与设计预期有两处偏差：（1）Copy2 的修复不是通过 bg_fg/选择器，而是通过新增 `pixel_colors` 基础设施；（2）pre_priority 的改善不是通过"差异类型一致性奖励"（设计 §5.3.1），而是通过更直接的 `mode=` 属性引用计数和 translate/crop 语义奖励。两者都是设计框架内的合理适配。

### 5.1 Layer 1 变更

#### 5.1.1 bg_fg 分割实现

新增 `bg_fg` 分割方案，核心逻辑：

1. 统计输入网格的颜色频率直方图。
2. 取频率最高的颜色为候选背景色 `bg_color`。若多种颜色并列最高频，按颜色数值升序取最小值（固定 tie-break，与 Step 1 对 cc4 背景色=0 的默认值一致）。
3. 将所有非 `bg_color` 像素按 4-连通分量提取为前景对象。
4. 构建 `SegmentationPlan(plan_id="bg_fg", method="bg_fg", objects=..., relations=...)`。
5. `bg_color` 作为 `SegmentationPlan` 的正式字段存储（`bg_color: int | None`），供 Layer 4 渲染时读取。同时在调试输出中可见。

在 `perceive_grid()` 的分割方案列表中追加 `bg_fg` 方案（在 cc4/cc8/whole_grid 之后）。

**与 cc4 的区别**：cc4 固定将颜色 0 视为背景；bg_fg 动态识别背景色。当背景色恰好是 0 时，bg_fg 与 cc4 结果可能相同。

#### 5.1.2 关系提取扩展

在 `extract_relations()` 中新增两个关系类型：

1. **adjacency**：对每对对象检查是否存在至少一个 4-邻域共享像素。实现上可遍历对象 A 的边界像素，检查其 4-邻域是否属于对象 B 的像素集。
2. **containment**：对每对对象检查 A 的 bbox 是否完全落在 B 的 bbox 内，即 `A.min_row >= B.min_row and A.min_col >= B.min_col and A.max_row <= B.max_row and A.max_col <= B.max_col`。

这两个关系对所有分割方案（cc4/cc8/whole_grid/bg_fg）都统一提取。

#### 5.1.3 nested 分割实现（可选）

若实现阶段判定 bg_fg 不足以覆盖 Center3 等任务的分割需求，启用 nested：

1. 先按 cc4 提取顶层连通分量。
2. 对每个顶层分量，提取其 bbox 内的像素子集，按 cc4 递归提取二级子分量。
3. 生成具有层级 ID 的对象：`nested:0`（顶层）、`nested:0:1`（子分量）。

是否实际启用在 Step 2a 实现过程中根据 Center3 的改善程度决定。

### 5.2 Layer 2 变更

#### 5.2.1 对齐适配

对齐子模块需适配 bg_fg 分割输出：

1. bg_fg 方案下的对象集只包含前景对象，对象数量可能少于 cc4/cc8（因为背景像素被排除）。
2. 对齐时不需要匹配背景色对象，减少无效匹配。
3. 对齐方法本身（像素重合、颜色+形状、二部匹配）不需要修改，只是输入对象集发生变化。

#### 5.2.2 候选模板扩展

为 Step 2a 修复目标，Layer 2 需要在现有候选模板基础上：

1. 为 bg_fg 分割方案生成使用新单对象选择器（`largest_object`）的候选；对象集选择器（`foreground_objects`、`noise_objects`）仅用于接受对象集的原语（`delete`、`recolor`）。
2. 确保 copy 类候选在 pre_priority 中不被 delete 类候选压制（具体策略见 §5.3）。

#### 5.2.3 差异识别扩展

Step 2a 沿用 Step 1 的差异类型，不新增。Step 2b 阶段新增差异类型（见 §8.2）。

### 5.3 Layer 3 变更

#### 5.3.1 pre_priority 改善

Step 1 的 `pre_priority` 只用 `attr_ref_ratio` 和 `ast_depth` 两个代理，在 Copy3/Copy4 上导致 copy 候选排在 delete 候选之后被截断。

Step 2a 的改善策略：

1. **差异类型一致性奖励**：若 Layer 2 识别的差异类型为"新增对象"，则 copy 类候选获得 pre_priority 加分；若差异类型为"消失对象"，则 delete 类候选获得加分。这不是新增代理特征，而是利用 Layer 2 已有的差异识别结果做一致性检查。
2. **beam 调整**：若 Step 2a 仍频繁出现 beam 饱和，允许上调 `STEP2_BEAM_SIZE`，但须在报告中记录。

#### 5.3.2 描述长度适配

`description_length` 的 AST 节点计数规则沿用 Step 1 终态，自动覆盖新原语（extend_to_boundary 等），因为新原语仍是 `PrimitiveCall` 节点。无需额外修改。

### 5.4 Layer 4 变更

#### 5.4.1 背景色修复

**关键修复**：将 `_background_color()` 从硬编码 `return 0` 改为从 `SegmentationPlan.bg_color` 读取。

在 `bg_fg` 分割方案下，`bg_color` 已由 Layer 1 识别并存储在 `SegmentationPlan` 中；在其他分割方案下，`bg_color` 为 `None`，回退到默认值 0。这直接解决 Step 1 实现设计 §6.4.2 记录的遗留问题。

#### 5.4.2 渲染规则扩展

渲染规则本身不变（四类输出尺寸规则、面积从大到小覆盖、越界截断），但背景色填充步骤改用动态识别的 `bg_color`。

### 5.5 Layer 5 变更

#### 5.5.1 归因增强

1. 在 `Attribution` 中新增 `concept_group` 字段。
2. 失败归因的 `failure_detail` 遵循架构文档的分类约束：
   - 当 `failure_type = SELECTION_FAIL` 时，`failure_detail` **必须**填入架构文档 §7.3.0 定义的硬枚举值：`PLAN_ERROR`、`ALIGNMENT_ERROR`、`CONSTRAINT_SUBSET_ERROR`、`PROGRAM_ERROR`，不允许自由文本。
   - 当 `failure_type` 为 `PERCEPTION_FAIL`、`ABSTRACTION_FAIL` 或 `EXECUTION_FAIL` 时，`failure_detail` 保持自由文本，鼓励填充更具体的信息（如"bg_fg 分割后仍无法形成稳定对齐"）。

## 6. Step 2a 验收标准

Step 2a 完成，必须同时满足：

1. Copy1-6 + Center1-6 共 12 个训练任务中，精确求解数 **≥9/12**。
2. Step 1 基线不回归：原来精确求解的 6 个任务（Copy1、Center1、Center2、Center4、Center5、Center6）仍全部精确求解。
3. 所有未解任务均有非空、可读且归因合理的输出。
4. 不依赖样例级 ad-hoc 特判。

### 6.1 Step 2a 实际结果（2026-04-05）

Step 2a 最终结果 **8/12**，未达 ≥9/12 门槛。逐项对照如下：

| 条件 | 状态 | 说明 |
| --- | --- | --- |
| ≥9/12 精确求解 | ❌ **未达标**（8/12） | 差 1 个到达门槛；4 个未解任务确认超出 Step 2 DSL 表达力 |
| Step 1 基线不回归 | ✅ 达标 | Copy1、Center1-2、Center4-6 全部 100% |
| 未解任务归因合理 | ✅ 达标 | Copy3-6 均有穷举验证的 ABSTRACTION_FAIL 归因 |
| 无 ad-hoc 特判 | ✅ 达标 | 所有修复均为通用机制（pixel_colors、bg_fg 改进、crop 语义奖励） |

**逐任务结果汇总**：

| 任务 | Step 1 | Step 2a | 选中程序 |
| --- | --- | --- | --- |
| Copy1 | ✅ 100% | ✅ 100% | `copy[target=all] ; on_copy: translate[target=all,dx=input_width,dy=0] ; on_original:` |
| Copy2 | ❌ 96.4% | ✅ 100% | `copy[target=smallest_object] ; on_copy: translate[target=all,dx=to_largest_object_center_dx,dy=to_largest_object_center_dy] ; on_original:` |
| Copy3 | ❌ 89.4% | ❌ 93.7% | `crop[target=center_object,mode=tight_bbox]` |
| Copy4 | ❌ 82.6% | ❌ 83.7% | `crop[target=center_object,mode=tight_bbox]` |
| Copy5 | ❌ 38.0% | ❌ 37.0% | `crop[target=cc4:0,mode=tight_bbox]` |
| Copy6 | ❌ 43.7% | ❌ 43.7% | `copy[target=largest_object] ; on_copy: ; on_original:` |
| Center1 | ✅ 100% | ✅ 100% | `fill[target=all,mode=center_cell]` |
| Center2 | ✅ 100% | ✅ 100% | `crop[target=center_object,mode=tight_bbox]` |
| Center3 | ❌ 2.1% | ✅ 100% | `crop[target=center_object,mode=tight_bbox]`（bg_fg 方案） |
| Center4 | ✅ 100% | ✅ 100% | `delete[target=all,mode=input_center_component]` |
| Center5 | ✅ 100% | ✅ 100% | `translate[target=all,mode=rare_color_motif_to_largest_component_center]` |
| Center6 | ✅ 100% | ✅ 100% | `translate[target=all,mode=rare_color_motif_to_largest_component_center]` |

**Step 2a 关键代码变更清单**：

1. **`data/models.py`**：`ObjectData` 新增 `pixel_colors: dict[Cell, int]` 字段。
2. **`layer1/objects.py`**：`extract_cc_objects` 新增 `same_color` 参数；`build_object` 和 `build_whole_grid_object` 填充 `pixel_colors`。
3. **`layer1/perception.py`**：bg_fg 路径使用 `same_color=True`。
4. **`layer3/scoring.py`**：`pre_priority` 计入 `mode=` 至 `attr_ref_count`；`_semantic_consistency_bonus` 新增 translate/crop 类型奖励（各 +0.15）。
5. **`layer4/executor.py`**：所有变换（translate、rotate、flip、recolor、fill、crop、extend_to_boundary、delete_center_component、normalize_objects）完整传播 `pixel_colors`；新增 `_rotate_once_with_colors`、`_flip_pixels_with_colors` 辅助函数。
6. **`layer4/render.py`**：`render_objects` 改为按 `pixel_colors` 着色。
7. **`runner/task_runner.py`**：bg_fg output 无前景对象时回退到 cc4 output 用于对齐。

**测试状态**：78 个单元测试全部通过。

**关于 ≥9/12 门槛的处理说明**：

8/12 距门槛差 1 个。未解的 4 个任务（Copy3-6）已通过穷举验证确认超出 Step 2 DSL 表达力边界（需要 anchor-relative 参数化位移或 repeat/tile），不是可通过继续调参来弥合的差距。在 Step 2 边界内，所有可修复的目标（Copy2、Center3）均已修复，没有遗漏的低垂果实。

根据 §4.7 原设计结论，≥9/12 被定义为"进取型目标"，且已预判"若最终 Copy 改善不足，应诚实归因"。当前结果符合该预判。建议将 8/12 作为 Step 2a 的诚实终态接受，并把 Copy3-6 的能力缺口正式登记为 Step 3 提前引入能力，而不是回流到 Step 2b 扩边界处理。

## 7. Step 2b 概念组引入顺序

Step 2b 的 4 个新概念组按以下顺序引入：

| 顺序 | 概念组 | 复杂度 | 核心操作 | 主要新能力依赖 |
| --- | --- | --- | --- | --- |
| 1 | MoveToBoundary | 低 | translate（已有） | to_boundary 参数、adjacency 关系 |
| 2 | ExtendToBoundary | 中 | extend_to_boundary（新增） | extend_to_boundary 原语 |
| 3 | ExtractObjects | 中-高 | delete/crop + 主体选择 | bg_fg 分割、largest_object 选择器、noise_objects 用于 delete |
| 4 | CleanUp | 高 | delete + 噪声识别 | noise_objects 选择器、bg_fg 分割 |

从易到难的顺序理由：

1. **MoveToBoundary** 最接近现有 translate 能力，只需补 boundary-aware 位移参数。
2. **ExtendToBoundary** 需要新原语，且方向解析要从常量方向放宽到封闭白名单的参数化方向，但仍限制在轴向延伸和最近对象边界语义内，不进入对角/放射式扩展。
3. **ExtractObjects** 需要前景/背景分离和主体选择，依赖 bg_fg 分割在前两组上验证稳定。
4. **CleanUp** 最复杂——需要噪声识别、可能需要输出尺寸模式切换。

每引入一组后，必须验证：
1. 该组的精确求解数达到组级验收标准（见 §10）。
2. 前序组和 Step 2a 结果不回归。
3. 新增代码不破坏已有接口。

## 8. Step 2b 各层增量变更

### 8.1 Layer 1 增量

Step 2b 的 Layer 1 不需要相对 Step 2a 的额外变更。bg_fg、adjacency、containment 在 Step 2a 已实现，直接复用。

若 ExtractObjects 或 CleanUp 需要 nested 分割，在此阶段启用（前提是 Step 2a 验收点之后）。

### 8.2 Layer 2 增量

#### 8.2.1 新差异类型

| 差异类型 | 对应概念组 | 对应候选原语 |
| --- | --- | --- |
| 位置变化（边界对齐） | MoveToBoundary | translate[..., to_boundary_*] |
| 形状延伸 | ExtendToBoundary | extend_to_boundary |
| 对象消失 + 尺寸缩小 | ExtractObjects | delete + crop_selected_bbox |
| 噪声像素消失 | CleanUp | delete[target=noise_objects] |

#### 8.2.2 候选模板

每个新概念组需要对应的候选生成模板：

**MoveToBoundary**：
```text
translate[target=X, dx=to_boundary_dx, dy=to_boundary_dy]
translate[target=X, dx=to_nearest_object_dx, dy=to_nearest_object_dy]
```

**ExtendToBoundary**：
```text
extend_to_boundary[target=X, source=S, direction=P]
```
其中 `source` 与 `direction` 都使用封闭白名单参数。

边界说明：`source` 与 `direction` 在单个假设内必须是常量 token，不允许按训练对或测试对动态切换。因此，像 ETB1 这类“同一统一规律需要根据对象几何关系在不同 pair 上改选 `center_row/right` 或 `center_col/down`”的任务，应判定为当前 7B 的 overflow，而不是继续通过 beam、scoring 或 target selector 微调来修补。

ETB4 的处理边界与 ETB1 不同：允许在 `target=X` 层新增一个封闭单对象选择器 `gap_thinner_object`，语义限定为“在两对象、单轴 gap 布局中，选择沿 gap 轴更细的对象作为 extend target”。这属于 target 选择层补全，不改写 `extend_to_boundary` 的 `source/direction` 白名单，也不引入 pair-conditioned direction 语义。

ETB5 的边界比 ETB1 更硬：其训练样本需要对角/放射式扩张，而当前 7B 只允许轴向延伸。实际分析结果也表明，ETB5 的候选池中 `extend_to_boundary` 假设数为 0，Layer 2 只会把它识别成 `copy / boundary_translate / fill / delete` 一类差异，因此应直接登记为 7B overflow，不再在本阶段继续尝试 beam、selector 或 source/direction 微调。

ETB6 与 ETB5 同类，也应直接登记为 7B overflow。它虽然出现了 beam 饱和，但根因并不是 beam 截断，而是任务所需的“沿对角方向延伸至边界”不在当前 DirectionSpec 白名单内；`match_extend_to_boundary_directions()` 只能枚举轴向 token，因此不会为 ETB6 生成 `extend_to_boundary` 候选，最终只会退化为 `crop / copy / translate` 一类近似解释。

据此，冻结当前 7B 语义边界后的阶段上界应明确记为 **2/6**：仅 ETB2（beam keepalive）与 ETB4（封闭 target selector）在不突破边界的前提下可稳定落地；ETB1、ETB3、ETB5、ETB6 都不应再继续作为 Step 2b 内部修补目标。

这 4 个未解任务对应的 Step 3 能力缺口可归并为一段统一结论：ETB1 需要按 pair 几何关系条件化选择 `source/direction`；ETB3 需要超出当前轴向 extend 的对角/构造式传播；ETB5 与 ETB6 需要对角或放射式边界延伸。它们的共同指向都是 Step 3 级别的“几何条件化方向策略 + 非轴向构造式扩张”能力，而不是继续增补 Step 2b 的白名单 token。

`source` 允许：

- `full_boundary`
- `top_edge / bottom_edge / left_edge / right_edge`
- `center_row / center_col`

`direction` 允许：

- 常量方向：`up / down / left / right`
- 画布边界方向：`nearest_boundary`
- 最近对象边界方向：`to_nearest_object_boundary`
- 双向轴延伸：`horizontal_both / vertical_both`

Step 2b 仍不放开对角延伸、放射式扩张、按样例动态生成新方向 token，也不放开任意掩码式 source 选择。

**ExtractObjects**：
```text
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
crop[target=largest_object, mode=tight_bbox]
```

当前 7C 验证结果已经达到最低门槛 **2/6**。现阶段的 exact pass 来自更保守的通用结构：ExtractObjects1 选中 `crop[target=largest_object,mode=tight_bbox]`，ExtractObjects3 选中单对象删除路径并配合 `crop_selected_bbox` 收口；这说明在当前代码基线下，`largest_object + crop_selected_bbox` 已足以覆盖最小验收目标，而显式 `delete[target=noise_objects] ; crop[...]` 仍保留为允许模板，但不是当前达标所必需的前提。

**CleanUp**：
```text
delete[target=noise_objects]
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
```

当前 7D 的基线验证结果仍是 **0/6**。更关键的是，直接脱离搜索流程执行这两条允许模板，在现有 `cc4 / cc8 / whole_grid / bg_fg` 分割与当前 executor 语义下也仍然是 **0/6**，最佳训练像素准确率大多只停在约 **0.89-0.95**。这说明 7D 的当前阻塞点并不只是“候选没放进 sketches”或“beam 没保活”。

当前已确认的能力缺口有两层：
1. `noise_objects` 的临时面积阈值启发式（`area < median/4`）在许多 CleanUp 任务上会返回空集，或者在大量单像素/碎片对象并存时缺乏稳定性。
2. 即使手工指定了应删除的噪声对象，当前 `delete[target=noise_objects]` 的执行语义也缺少“删除后恢复结构化底纹”的能力；它只能在现有对象渲染规则下去掉像素，无法稳定重建条纹、棋盘、嵌套主体周围的原有局部结构。

因此，7D 目前不应被当作“再补一个模板就能收口”的子阶段，而应明确记为：需要更强的 `noise_objects` 选择稳定性，以及面向结构化背景的局部修复/恢复语义；在这两点未补齐前，不做达标宣告。

补充红线：即使后续决定在 Step 2 中尝试引入“局部修复/恢复语义”，它也只能依赖局部上下文一致性，不能依赖任务名、颜色特判、图样类别特判，也不能按样例切换规则。若某一版实现必须借助这些信息才能成立，则应直接记为 Step 3 能力，而不是在 Step 2 中继续扩边界。

补充实验结论：在上述红线下，已做过一轮受限原型验证。原型只允许基于当前 plan 的对象统计选择噪声对象，并只允许用行/列/邻域一致性做局部恢复。结果最好只能达到 **1/6** exact，且唯一稳定精确的是 CleanUp2。这说明“局部一致性修复”方向并非完全错误，但当前证据仍不足以支持把它工程化接入 Step 2 主线；更合理的口径是保留这 1 例作为实验信号，而不是把它当作已验证的 7D 能力。

以上为代表性模板，实际候选由 Layer 2 的差异识别驱动枚举。

### 8.3 Layer 3 增量

`description_length` 和 `pre_priority` 的计算规则自动适配新原语（因为新原语仍使用 `PrimitiveCall` 数据结构）。

若新概念组的候选空间显著大于 Copy/Center，可能需要上调 `STEP2_BEAM_SIZE`。具体数值在实现阶段根据 beam_saturated 统计决定。

对 ExtendToBoundary 允许一条更窄的局部搜索保活策略：当 `beam_saturated=true`、全局 top-`STEP2_BEAM_SIZE` 中完全没有 `extend_to_boundary`、但排序靠后的候选中存在 `extend_to_boundary` 时，允许在不改动全局 `pre_priority` 的前提下，额外追加 **1 个** `extend_to_boundary` keepalive 槽位进入评估。该策略只解决“正确原语家族整体缺席 beam”的问题，不得改写 7B 的 source/direction 语义，也不得推广成任意原语的通用加权捷径。

### 8.4 Layer 4 增量

#### 8.4.1 extend_to_boundary 执行逻辑

```text
输入：对象 O、source 参数 S、方向参数 P、网格 G
输出：延伸后的对象 O'

1. 先根据 source 参数 S 从 O 中选出候选源像素集合：
   a. `full_boundary`：O 的全部像素。
   b. `top_edge / bottom_edge / left_edge / right_edge`：分别取 bbox 对应边上的像素。
   c. `center_row / center_col`：分别取 bbox 中心最近的行或列；若偶数宽高导致并列，固定取索引较小者。
2. 再把方向参数 P 解析为一个或两个轴向射线：
    a. `up / down / left / right`：直接解析为单一射线。
    b. `nearest_boundary`：计算对象到上下左右四个画布边界的距离，选择最近方向；等距时固定按 `up > down > left > right`。
    c. `to_nearest_object_boundary`：在除 O 之外的对象中选择最近对象 N，再取“从 O 指向 N 最近边界”的轴向方向；并列时优先正交投影有重叠者，再按对象 id 字典序，最后按 `up > down > left > right`。
    d. `horizontal_both`：解析为 `left + right` 两条独立射线。
    e. `vertical_both`：解析为 `up + down` 两条独立射线。
3. 对每条射线，只在 source 集合内部选取该方向上的前沿像素作为起点，再沿该方向逐像素扩展。
4. 每条射线独立应用终止条件：
    a. 触及网格边界（row < 0 或 row >= height 或 col < 0 或 col >= width）。
    b. 触及另一个非背景对象的像素。
5. 将所有射线新增的像素与 O 原像素求并集，得到 O'。
6. O' 的颜色沿用 O 的 dominant_color；若对象携带 `pixel_colors`，则新增像素沿用其延伸源边界像素的颜色映射。
```

补充边界：Step 2b 的 `extend_to_boundary` 只允许上述封闭白名单的 `source` 与 `direction` 参数，不允许 diagonal、radial、flood-fill 式延伸，也不允许把 source/direction 解析外包给 ForEach/If/表达式树。

#### 8.4.2 渲染规则

Step 2b 沿用 Step 2a 的渲染规则（含动态背景色）。`crop_selected_bbox` 在 ExtractObjects 上的行为：输出画布尺寸 = 选中主体对象的 bbox 尺寸，背景色填充后叠加该对象的像素。

补充说明：这一渲染规则对 ExtractObjects 已足够，但对当前 7D / CleanUp 仍不充分。CleanUp 的若干训练任务要求在删除噪声后恢复非均匀底纹或主体边缘局部结构，而不是简单暴露统一 `bg_color`；这正是当前 7D 保持 0/6 的核心原因之一。

进一步约束：若后续真的为 CleanUp 增加修复语义，它必须表现为封闭、统一的局部一致性规则，例如固定的行/列/邻域一致性 tie-break，而不能演化成“看到条纹用一套、看到棋盘用一套、看到某种颜色再换一套”的外观驱动补丁。

### 8.5 Layer 5 增量

归因输出填充 `concept_group` 字段。失败归因逻辑不变。

## 9. 数据加载扩展

`loader.py` 需要扩展以支持 6 个概念组：

```python
STEP2_CONCEPT_GROUPS = ["Copy", "Center", "MoveToBoundary", "ExtendToBoundary", "ExtractObjects", "CleanUp"]

STEP2_TRAIN_TASKS = [
    *[_task_tuple(group, f"{group}{i}") for group in STEP2_CONCEPT_GROUPS for i in range(1, 7)],
]

STEP2_DIAGNOSTIC_TASKS = [
    *[_task_tuple(group, f"{group}{i}") for group in STEP2_CONCEPT_GROUPS for i in range(7, 11)],
]
```

`batch_runner.py` 扩展：
1. 支持按概念组分组运行（`--group MoveToBoundary`）。
2. 支持按子阶段运行（`--stage 2a` 只跑 Copy/Center，`--stage 2b` 跑全部 6 组）。
3. 输出按概念组分组的统计摘要。

## 10. 各概念组验收标准

各概念组的验收/跟踪口径如下：

| 概念组 | 训练任务数 | 最低精确求解数 | 说明 |
| --- | --- | --- | --- |
| Copy（Step 2a） | 6 | ≥2 | Step 1 的 1/6 保持或小幅提升；多数失败涉及对象组复制/repeat，超出 Step 2 表达力。**实际 2/6**（Copy1 + Copy2） |
| Center（Step 2a） | 6 | ≥6 | 从 Step 1 的 5/6 提升，Center3 为 bg_fg 高信心修复目标。**实际 6/6** |
| MoveToBoundary | 6 | ≥3 | 初始目标 |
| ExtendToBoundary | 6 | ≥3 | 初始目标 |
| ExtractObjects | 6 | ≥2 | 初始目标，难度较高。**当前 2/6**（ExtractObjects1 + ExtractObjects3） |
| CleanUp | 6 | 冻结缺口 | 当前不再作为 Step 2 内待收口组；保留为冻结的未收口能力缺口，并继续记录基线、原型与归因。 |

说明：

1. **Step 2a 的正式通过条件只以 §6 为准**：硬门槛是 Copy/Center 合计 ≥9/12 且 Step 1 基线不回归。表中的 Copy ≥2、Center ≥6 主要用于跟踪每组进展和约束预期实现路径，不构成独立于 §6 之外的额外否决条件。
2. 因此，若出现 Copy=1、Center=8 这类总计已达 ≥9/12 且基线不回归的结果，Step 2a 仍视为通过；但实验报告应说明其实现路径与原预期不一致。
3. Step 2b 各组的"初始目标"是保守下限。若新能力（bg_fg、extend_to_boundary 等）在某组上表现良好，实际求解数可超过下限。
4. 若某组低于最低求解数，须在实验报告中分析根因并说明是否超出 Step 2 表达力边界。

## 11. 代码组织

### 11.1 从 step1/ 到 step2/ 的演进规则

1. **首次创建**：将 `phase1/src/step1/` 完整复制为 `phase1/src/step2/`。
2. **修改约束**：所有 Step 2 代码变更只在 `step2/` 目录下进行，不触及 `step1/`。
3. **导入路径**：`step2/` 内部的导入路径全部改为 `phase1.src.step2.*`。
4. **配置分离**：`step2/config.py` 独立维护 Step 2 的白名单、任务清单和常量。

### 11.2 共享工具代码

`step1/utils/` 下的工具函数（timing、ids、debug_dump）若在 step2 中无需变更，可从 step1 导入以避免代码重复。但层级模块（layer1-5）必须在 step2/ 内独立维护，因为它们包含 Step 2 特有的扩展逻辑。

### 11.3 输出目录

Step 2 输出放在 `phase1/outputs/step2/`，目录结构与 step1 相同：

```text
phase1/outputs/step2/
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

## 12. 测试策略

### 12.1 单层测试

在 Step 1 测试基础上新增：

| 层 | 新增最小测试 |
| --- | --- |
| Layer 1 | bg_fg 分割结果稳定，对象数和 bg_color 可人工验证；adjacency 和 containment 关系正确 |
| Layer 2 | bg_fg 分割下的对齐结果稳定，alignment_id 绑定不丢失 |
| Layer 3 | 新候选空间下 pre_priority 排序合理，copy 类不被系统性压制 |
| Layer 4 | extend_to_boundary 在 source=`full_boundary/top_edge/bottom_edge/left_edge/right_edge/center_row/center_col` 与 `up/down/left/right`、`nearest_boundary`、`to_nearest_object_boundary`、`horizontal_both`、`vertical_both` 的组合上做最小独立执行测试；背景色动态识别测试 |
| Layer 5 | concept_group 字段正确填充 |

### 12.2 端到端测试

Step 2 的端到端测试分多轮推进（仅使用训练任务）：

**Step 2a 阶段：**
1. 先验证 Step 1 基线：在 step2/ 代码上跑 Copy1-6 + Center1-6，确认 6/12 基线不退化。
2. 启用 bg_fg 分割后重新运行，对比改善。
3. 全部 Step 2a 变更后运行，验证 ≥9/12。

**Step 2b 阶段：**
1. 每引入一个新概念组后运行该组 1-6 训练任务。
2. 同时回跑 Step 2a 的 12 个任务，确认无回归。
3. 全部 4 组引入后运行完整 36 训练任务批量测试。

### 12.3 人工审查

Step 2 结束前，至少人工抽查：

1. 3 个 Step 2a 中从失败变为成功的任务。
2. 每个新概念组至少 1 个成功 + 1 个失败任务。

抽查内容与 Step 1 相同：对象图、对齐、程序可读性、failure_type 一致性。

## 13. 遥测与调试产物

Step 2 沿用 Step 1 的遥测产物（Attribution JSON、timing JSON、选中 hypothesis 摘要），新增：

1. **概念组级聚合**：`summary.json` 和 `summary.md` 中按概念组分组统计。
2. **bg_fg 诊断**：每个任务的调试输出中记录 `bg_color` 识别结果。
3. **回归检测**：批量运行报告中标记相对 Step 1 基线的回归任务。

推荐 `summary.md` 格式：

```markdown
# Step 2 Summary

## Overall
- total_tasks: 36
- exact_solved: ?
- overall_accuracy: ?

## By Concept Group
| Group | Tasks | Solved | Accuracy | Regressions |
| --- | --- | --- | --- | --- |
| Copy | 6 | ? | ? | ? |
| Center | 6 | ? | ? | ? |
| MoveToBoundary | 6 | ? | ? | N/A |
| ExtendToBoundary | 6 | ? | ? | N/A |
| ExtractObjects | 6 | ? | ? | N/A |
| CleanUp | 6 | 冻结缺口 | 0/6 | 不作为当前已收口组处理 |

## Failure Type Distribution
...

## Average Layer Times (ms)
...
```

## 14. Step 2 整体验收

Step 2 完成，必须同时满足以下所有条件：

> **2026-04-06 全量回归快照**：已对 36 个训练任务完成 Phase 9 全量回归，整体结果为 **15/36 exact**，无已知成功样例回归。概念组结果为：Copy **2/6**、Center **6/6**、MoveToBoundary **3/6**、ExtendToBoundary **2/6**、ExtractObjects **2/6**、CleanUp **0/6**。其中 MoveToBoundary、冻结后的 ExtendToBoundary、ExtractObjects 均满足当前组级口径；CleanUp 继续作为冻结的未收口能力缺口保留。需要明确的是，这一结果仍**不足以宣告 Step 2 整体完成**，因为 Step 2a 目前仍为 **8/12**，未达到本节要求的 **≥9/12**。

### 14.1 定量门槛

1. Step 2a：Copy/Center 合计精确求解 ≥9/12。
2. Step 2a：Step 1 基线不回归（6 个原成功任务仍全部成功）。
3. Step 2b：4 个新增概念组达到 §10 中的最低精确求解数。
4. 全部 36 训练任务的失败归因都非空且合理。

### 14.2 定性门槛

1. 系统未依赖样例级 ad-hoc 特判。
2. 新增原语和分割/对齐规则有明确的任务驱动依据。
3. 每加一组后系统仍保持可重复求解，不需要重写架构。
4. 归因输出至少能把"分割不足"和"原语表达力不足"区分开；这构成 Step 2 完成的最低归因粒度。进一步稳定区分"对齐失败"属于 Step 3 准入门槛，见 §16.1。

### 14.3 工程门槛

1. 所有单层测试和端到端测试通过。
2. step1/ 代码未被修改。
3. 遥测产物和调试输出完整落盘。

## 15. 退出条件

出现以下任一情况，Step 2 应暂停并回到设计层修订：

1. bg_fg 分割在多数任务上产生的前景对象数不合理（显著多于或少于预期）。
2. 新原语（extend_to_boundary 等）的语义在跨任务泛化时不一致。
3. 新概念组的 beam 饱和率显著高于 Copy/Center，且调整 BEAM_SIZE 后仍无改善。
4. Step 2a 结果持续低于 ≥9/12，且无法确定是分割问题还是表达力问题。
5. Layer 5 的归因标签无法和实际调试证据对齐。

## 16. 与 Step 3 衔接

Step 2 完成并不自动等于具备 Step 3 准入资格。允许进入 Step 3 的前提是以下条件全部满足（参见架构文档 §12.2 成功标准）：

### 16.1 必要前提

1. **稳定性**：至少在 6 个概念组上保持可重复求解，加组不需要重写架构。
2. **区分能力**：归因输出能稳定区分"对齐失败"、"分割不足"和"程序表达力不足"三类失败。若此能力不具备，不得进入 Step 3。
3. **搜索预算**：据实报告 beam/timeout 的实际使用情况，为 Step 3 设定真实预算提供依据。
4. **新原语清晰**：所有 Step 2 启用的原语语义明确，不再依赖样例级特判。

### 16.2 Step 3 预计方向

基于架构文档 §12.3，Step 3 预计方向包括：

1. 启用知识状态写回、扩展准入、假设库。
2. 启用排序模型训练。
3. 扩展到更多概念组（参照架构 §11.7 的渐进扩展序列）。
4. 启用 bbox/repeat 分割策略。
5. 启用 scale、conditional_map 等高阶原语。
6. 提前引入经 Step 2a 验证附录确认的能力缺口：
    - Copy3/4 → 参数化 anchor-relative 位移语义
    - Copy5/6 → repeat / tile / construct_grid 一类构造语义

Step 2 为 Step 3 提供的关键交付物：

1. 稳定的六组求解器代码基线。
2. 完整的失败归因数据集（含所有未解任务的 failure_type 和 failure_detail）。
3. 搜索统计（beam 使用率、候选数、各层耗时）作为 Step 3 预算设定依据。
4. 明确的能力缺口列表：哪些任务因分割不足而失败、哪些因原语不足而失败。
