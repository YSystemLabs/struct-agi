# 第一阶段 Step 2 实现设计

> 版本：v0.1
>
> 状态：草案
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
│       │   ├── dsl.py                # 新增 extend_to_boundary（按需 merge）解析
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

Step 1 终态 6/12，6 个失败任务的根因分析如下。

### 4.1 Copy2（像素准确率 96.4%，ABSTRACTION_FAIL）

**选中程序**：`copy[target=smallest_object] ; on_copy: translate[...dx=to_largest_object_center_dx,...] ; on_original:`

**失败原因**：`smallest_object` 选择器在跨 train pair 时不稳定。不同 pair 中"最小对象"的语义不一致——有些 pair 中最小对象是待复制的源图样，有些 pair 中是噪声碎片。

**Step 2 修复方向**：
1. `bg_fg` 分割可把噪声碎片归入背景，使前景对象集更干净，`smallest_object` 选中的对象更稳定。
2. 新增 `foreground_objects` 选择器提供基于 bg_fg 的对象筛选。

### 4.2 Copy3（像素准确率 89.4%，ABSTRACTION_FAIL，beam_saturated）

**选中程序**：`delete[target=all,mode=input_center_component]`

**失败原因**：操作类型混淆——正确操作应是 copy 而非 delete。beam 饱和（184 候选 → 64 评估）导致正确候选被截断。

**Step 2 修复方向**：
1. 改善 `pre_priority` 预排序，使 copy 类候选排在 delete 类候选之前（当差异特征更接近"新增对象"而非"消失对象"时）。
2. 考虑上调 BEAM_SIZE 或改善候选去重，减少 beam 饱和影响。

### 4.3 Copy4（像素准确率 82.6%，ABSTRACTION_FAIL，beam_saturated）

**选中程序**：`delete[target=cc4:5]`

**失败原因**：与 Copy3 类似，beam 饱和导致正确候选被截断，错误选中 delete 而非 copy 操作。

**Step 2 修复方向**：同 Copy3。

### 4.4 Copy5（像素准确率 38.0%，ABSTRACTION_FAIL）

**选中程序**：`crop[target=cc4:0,mode=tight_bbox]`

**失败原因**：crop 目标识别失败。系统选中了错误的对象（cc4:0），且 crop 操作本身不足以表达该任务的真实变换规则。

**Step 2 修复方向**：
1. `bg_fg` 分割提供更好的前景/背景分离。
2. 新增 `largest_object` 选择器提供更稳定的目标选择。
3. 若该任务涉及块级重复或构造性变换，可能仍超出 Step 2 表达力范围，此时归因为 ABSTRACTION_FAIL 并记录为 Step 3 候选。

### 4.5 Copy6（像素准确率 43.7%，ABSTRACTION_FAIL）

**选中程序**：`copy[target=smallest_object] ; on_copy: translate[...dx=to_largest_object_center_dx,...] ; on_original:`

**失败原因**：与 Copy2 类似，`smallest_object` 选择器泛化不足。同时，候选只覆盖了单次搬运，而该任务可能涉及更复杂的多对象放置。

**Step 2 修复方向**：
1. 同 Copy2 的 bg_fg + 新选择器方向。
2. 若真实变换涉及多锚点放置或 repeat，在 Step 2 边界内无法解决，归因并移交 Step 3。

### 4.6 Center3（像素准确率 2.1%，ABSTRACTION_FAIL）

**选中程序**：`delete[target=cc8:0]`

**失败原因**：灾难性失败。cc4/cc8 无法把嵌套在背景中的前景主体正确分离，导致对齐和候选生成全面偏差。2.1% 的像素准确率说明错误不在候选筛选，而在感知层。

**Step 2 修复方向**：
1. **最高优先级**：`bg_fg` 分割直接解决 Center3 的核心感知问题。通过频率分析识别背景色后，前景对象可被正确分离。
2. 若 `bg_fg` 不足，启用 `nested` 分割做两级递归提取。
3. `containment` 关系帮助识别嵌套结构中的主体与容器对象。

### 4.7 失败分布汇总

| 失败类别 | 任务 | 共同根因 | Step 2 主要修复手段 |
| --- | --- | --- | --- |
| 选择器泛化不足 | Copy2, Copy6 | smallest_object 跨 pair 不稳定 | bg_fg 分割 + 新选择器 |
| 操作类型混淆 + beam 饱和 | Copy3, Copy4 | 正确候选被截断 | pre_priority 改善 + beam 调整 |
| 目标识别失败 | Copy5 | crop 选中错误对象 | bg_fg + largest_object 选择器 |
| 感知层灾难性失败 | Center3 | cc4/cc8 无法分离嵌套结构 | bg_fg（+ 可选 nested）分割 |

## 5. Step 2a 各层变更设计

### 5.1 Layer 1 变更

#### 5.1.1 bg_fg 分割实现

新增 `bg_fg` 分割方案，核心逻辑：

1. 统计输入网格的颜色频率直方图。
2. 取频率最高的颜色为候选背景色 `bg_color`。
3. 将所有非 `bg_color` 像素按 4-连通分量提取为前景对象。
4. 构建 `SegmentationPlan(plan_id="bg_fg", method="bg_fg", objects=..., relations=...)`。
5. `bg_color` 作为方案级元数据记录在调试输出中。

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

1. 为 bg_fg 分割方案生成使用新选择器（`largest_object`、`foreground_objects`）的候选。
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

**关键修复**：将 `_background_color()` 从硬编码 `return 0` 改为接受 `bg_color` 参数。

在 `bg_fg` 分割方案下，使用 Layer 1 识别的候选背景色；在其他分割方案下，保持默认值 0。这直接解决 Step 1 实现设计 §6.4.2 记录的遗留问题。

#### 5.4.2 渲染规则扩展

渲染规则本身不变（四类输出尺寸规则、面积从大到小覆盖、越界截断），但背景色填充步骤改用动态识别的 `bg_color`。

### 5.5 Layer 5 变更

#### 5.5.1 归因增强

1. 在 `Attribution` 中新增 `concept_group` 字段。
2. 失败归因的 `failure_detail` 在 Step 2 中鼓励填充更具体的信息（如"bg_fg 分割后仍无法形成稳定对齐"），但不强制要求结构化。

## 6. Step 2a 验收标准

Step 2a 完成，必须同时满足：

1. Copy1-6 + Center1-6 共 12 个训练任务中，精确求解数 **≥9/12**。
2. Step 1 基线不回归：原来精确求解的 6 个任务（Copy1、Center1、Center2、Center4、Center5、Center6）仍全部精确求解。
3. 所有未解任务均有非空、可读且归因合理的输出。
4. 不依赖样例级 ad-hoc 特判。

## 7. Step 2b 概念组引入顺序

Step 2b 的 4 个新概念组按以下顺序引入：

| 顺序 | 概念组 | 复杂度 | 核心操作 | 主要新能力依赖 |
| --- | --- | --- | --- | --- |
| 1 | MoveToBoundary | 低 | translate（已有） | to_boundary 参数、adjacency 关系 |
| 2 | ExtendToBoundary | 中 | extend_to_boundary（新增） | extend_to_boundary 原语 |
| 3 | ExtractObjects | 中-高 | delete/crop + 主体选择 | bg_fg 分割、largest_object / foreground_objects 选择器 |
| 4 | CleanUp | 高 | delete + 噪声识别 | noise_objects 选择器、按需 merge |

从易到难的顺序理由：

1. **MoveToBoundary** 最接近现有 translate 能力，只需补 boundary-aware 位移参数。
2. **ExtendToBoundary** 需要新原语但变换模式简单（单方向延伸）。
3. **ExtractObjects** 需要前景/背景分离和主体选择，依赖 bg_fg 分割在前两组上验证稳定。
4. **CleanUp** 最复杂——需要噪声识别、可能需要输出尺寸模式切换、可能需要 merge 原语。

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
extend_to_boundary[target=X, direction=D]
```
其中 `direction ∈ {up, down, left, right, nearest_boundary}`。

**ExtractObjects**：
```text
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
crop[target=foreground_objects, mode=tight_bbox]
```

**CleanUp**：
```text
delete[target=noise_objects]
delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]
recolor[target=noise_objects, color=bg_color]
```

以上为代表性模板，实际候选由 Layer 2 的差异识别驱动枚举。

### 8.3 Layer 3 增量

`description_length` 和 `pre_priority` 的计算规则自动适配新原语（因为新原语仍使用 `PrimitiveCall` 数据结构）。

若新概念组的候选空间显著大于 Copy/Center，可能需要上调 `STEP2_BEAM_SIZE`。具体数值在实现阶段根据 beam_saturated 统计决定。

### 8.4 Layer 4 增量

#### 8.4.1 extend_to_boundary 执行逻辑

```text
输入：对象 O、方向 D、网格 G
输出：延伸后的对象 O'

1. 确定延伸方向 D 对应的坐标轴和正负方向。
2. 从 O 的边界像素出发，沿 D 方向逐像素扩展。
3. 终止条件：
   a. 触及网格边界（row < 0 或 row >= height 或 col < 0 或 col >= width）。
   b. 触及另一个非背景对象的像素。
4. 将扩展的像素集合并入 O，得到 O'。
5. O' 的颜色沿用 O 的 dominant_color。
```

`nearest_boundary` 方向：计算对象到上下左右四个画布边界的距离，选择最近的方向延伸。

#### 8.4.2 merge 执行逻辑（若启用）

```text
输入：对象集 [O1, O2, ..., On]
输出：合并后的单一对象 O_merged

1. O_merged.pixels = O1.pixels ∪ O2.pixels ∪ ... ∪ On.pixels。
2. O_merged.bbox = 所有对象 bbox 的最小外接矩形。
3. O_merged.attrs 的颜色取像素集中频率最高的颜色。
```

#### 8.4.3 渲染规则

Step 2b 沿用 Step 2a 的渲染规则（含动态背景色）。`crop_selected_bbox` 在 ExtractObjects 上的行为：输出画布尺寸 = 选中主体对象的 bbox 尺寸，背景色填充后叠加该对象的像素。

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

各概念组独立验收标准：

| 概念组 | 训练任务数 | 最低精确求解数 | 说明 |
| --- | --- | --- | --- |
| Copy（Step 2a） | 6 | ≥4 | 从 Step 1 的 1/6 提升 |
| Center（Step 2a） | 6 | ≥5 | 从 Step 1 的 5/6 保持或提升 |
| MoveToBoundary | 6 | ≥3 | 初始目标 |
| ExtendToBoundary | 6 | ≥3 | 初始目标 |
| ExtractObjects | 6 | ≥2 | 初始目标，难度较高 |
| CleanUp | 6 | ≥2 | 初始目标，难度最高 |

说明：

1. Step 2a 合计 ≥9/12 的整体目标约束优先于单组目标——例如 Copy ≥3 + Center ≥6 = 9 也可接受。
2. Step 2b 各组的"初始目标"是保守下限。若新能力（bg_fg、extend_to_boundary 等）在某组上表现良好，实际求解数可超过下限。
3. 若某组低于最低求解数，须在实验报告中分析根因并说明是否超出 Step 2 表达力边界。

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
| Layer 4 | extend_to_boundary 在四个方向上的独立执行测试；背景色动态识别测试 |
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
| CleanUp | 6 | ? | ? | N/A |

## Failure Type Distribution
...

## Average Layer Times (ms)
...
```

## 14. Step 2 整体验收

Step 2 完成，必须同时满足以下所有条件：

### 14.1 定量门槛

1. Step 2a：Copy/Center 合计精确求解 ≥9/12。
2. Step 2a：Step 1 基线不回归（6 个原成功任务仍全部成功）。
3. Step 2b：各概念组达到 §10 中的最低精确求解数。
4. 全部 36 训练任务的失败归因都非空且合理。

### 14.2 定性门槛

1. 系统未依赖样例级 ad-hoc 特判。
2. 新增原语和分割/对齐规则有明确的任务驱动依据。
3. 每加一组后系统仍保持可重复求解，不需要重写架构。
4. 归因输出能把"分割不足"和"原语表达力不足"区分开。

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

Step 2 完成后，允许进入 Step 3 的前提是以下条件全部满足（参见架构文档 §12.2 成功标准）：

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

Step 2 为 Step 3 提供的关键交付物：

1. 稳定的六组求解器代码基线。
2. 完整的失败归因数据集（含所有未解任务的 failure_type 和 failure_detail）。
3. 搜索统计（beam 使用率、候选数、各层耗时）作为 Step 3 预算设定依据。
4. 明确的能力缺口列表：哪些任务因分割不足而失败、哪些因原语不足而失败。
