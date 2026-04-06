# 第一阶段 Step 2b 实验与验收报告

> 版本：v0.1
>
> 状态：已验收（仅 Step 2b 范围）
>
> 日期：2026-04-06
>
> 作用：汇总 Step 2b 的实验设置、关键结果、冻结边界、以及验收结论。

## 1. 实验目标与范围

Step 2b 的目标不是重新打开 Step 2a 的边界，而是在 Step 2a 已形成 **8/12、有条件通过** 的前提下，按文档规定顺序为 4 个新增概念组建立可审计的最小求解能力，并补齐批量 runner、遥测、概念组聚合与回归标记等中性基础设施。

Step 2b 覆盖的新增训练任务范围为 MoveToBoundary1-6、ExtendToBoundary1-6、ExtractObjects1-6、CleanUp1-6 共 24 个任务；同时要求持续回跑 Step 2a 的 Copy + Center 12 个训练任务，确保前序结果不回归。

Step 2b 明确不承接 Step 2a 已确认越界的任务缺口。Copy3-6 在 Step 2a 结束时已登记为 Step 3 提前引入能力，因此不允许在 Step 2b 里通过扩 DSL、扩语义或样例级补丁回流修复。

## 2. 实验设置

本次实验使用 [Step2实现设计-0v1.md](Step2实现设计-0v1.md)、[Step2最小接口与任务清单附录-0v1.md](Step2最小接口与任务清单附录-0v1.md) 和 [Step2实现任务分解清单-0v1.md](Step2实现任务分解清单-0v1.md) 作为冻结边界。实现采用 Python 标准库与 unittest，不使用第三方依赖、隐藏缓存或随机性。

Step 2b 运行配置如下：

1. 分割方案默认使用 cc4、cc8、whole_grid、bg_fg；nested 仍保持默认关闭。
2. 原语范围在 Step 2a 基础上继续使用 extend_to_boundary，并为 ExtractObjects / CleanUp 保持 delete + crop_selected_bbox 路径。
3. Layer 3 继续使用 `STEP2_BEAM_SIZE = 64`，仅对 ExtendToBoundary 允许 1 个局部 keepalive 槽位，避免正确原语家族在 beam 截断前整体缺席。
4. Step 2b runner 新增 `--stage 2a|2b|all` 与 `--group` 过滤，并自动输出概念组聚合、`regression_flags.json`、以及任务级诊断产物。
5. Phase 9 全量回归使用如下命令完成：

```bash
python3 -m phase1.src.step2.runner.batch_runner --output-dir phase1/outputs/phase9_full --stage all
```

当前正式验收引用的批量报告为 [summary.json](phase1/outputs/phase9_full/reports/summary.json)、[summary.md](phase1/outputs/phase9_full/reports/summary.md)、[regression_flags.json](phase1/outputs/phase9_full/reports/regression_flags.json) 与 [attributions.json](phase1/outputs/phase9_full/reports/attributions.json)。

## 3. 关键实现与边界收口

### 3.1 MoveToBoundary：从候选存在但被错杀，到 3/6 稳定达标

MoveToBoundary 的关键问题不是缺假设，而是正确位移族在排序里长期吃亏。修复点主要有两类：

1. 在 Layer 2 / Layer 4 中打通 `to_boundary_dx/dy` 与 `to_nearest_object_dx/dy` 的符号位移语义。
2. 在 Layer 3 的 `pre_priority` 中把这些 Step 2b 的符号参数按属性引用计入，避免边界感知位移被普通常数位移系统性压制。

最终 MoveToBoundary1、3、5 精确通过，达到 **3/6**，满足本组最低门槛。

### 3.2 ExtendToBoundary：边界内能力完成收口，边界外任务冻结转交 Step 3

ExtendToBoundary 是 Step 2b 中最需要谨慎控边界的概念组。本轮实施没有把它做成开放式构造语义，而是维持在封闭白名单内：

1. `extend_to_boundary` 参数从单一常量方向扩展为封闭的 `source + direction` 组合。
2. `direction` 仅允许 `up/down/left/right/nearest_boundary/to_nearest_object_boundary/horizontal_both/vertical_both`。
3. `source` 仅允许 `full_boundary/top_edge/bottom_edge/left_edge/right_edge/center_row/center_col`。
4. 新增局部 keepalive 和封闭 target selector `gap_thinner_object`，分别解决 ETB2 的家族存活问题和 ETB4 的 relation-conditioned target selection 问题。

验证结果表明，当前 7B 语义边界的现实上界为 **2/6**，即 ExtendToBoundary2 和 ExtendToBoundary4。ETB1、ETB3、ETB5、ETB6 已明确归因为 Step 3 能力缺口，不再继续在 Step 2b 中修补。

### 3.3 ExtractObjects：最低门槛由通用结构达成

ExtractObjects 没有通过额外 ad hoc 搜索扩张达标，而是由当前更通用的 `largest_object + crop_selected_bbox` 与单对象删除路径直接达成最小门槛。当前精确通过的是 ExtractObjects1 和 ExtractObjects3，整体为 **2/6**。

这说明 Step 2b 在该组上并不需要为了模板对称性继续扩大搜索空间，只需保留当前诚实口径即可。

### 3.4 CleanUp：真实验证后冻结为未收口能力缺口

CleanUp 是 Step 2b 中唯一没有以“达标”收尾的概念组，但它也不是“还差最后一补丁”的状态。当前已经完成以下验证：

1. 真实 batch 基线为 **0/6** exact。
2. 即使绕过搜索，直接执行 `delete[target=noise_objects]` 与 `delete[target=noise_objects] ; crop[target=largest_object, mode=tight_bbox]` 也仍是 **0/6**。
3. 在“只依赖局部上下文一致性，不允许任务名/颜色/图样特判”的红线下，局部修复原型最好只能达到 **1/6** exact，且只有 CleanUp2 稳定精确。

据此，CleanUp 在 Step 2b 中被正式记为“冻结的未收口能力缺口”，而不是待继续追指标的在界问题。

### 3.5 Phase 8：中性基础设施已完成落地

Step 2b 后段补齐了此前缺失的 runner / 遥测 / 报告收口能力：

1. `batch_runner.py` 支持按阶段、按概念组跑批。
2. `summary.json` / `summary.md` 输出概念组聚合结果。
3. `regression_flags.json` 自动标记已知成功样例是否回退。
4. `task_runner.py` 在调试产物中写出 `bg_color`、对象面积分布、以及 `noise_objects` 阈值与命中数量。

这部分属于中性基础设施，不应被误写成 CleanUp 已收口的证据；它的作用是把 Step 2b 的验收结果变成可重复、可审计的报告流程。

## 4. 实验结果

### 4.1 Step 2b 四组核心指标

截至 2026-04-06，Phase 9 的全量回归摘要见 [summary.json](phase1/outputs/phase9_full/reports/summary.json) 与 [summary.md](phase1/outputs/phase9_full/reports/summary.md)，四个 Step 2b 概念组结果如下：

| 概念组 | 当前验收口径 | 实际结果 | 平均像素精度 | 当前状态 | 说明 |
|------|-------------|---------|-------------|---------|------|
| MoveToBoundary | ≥3/6 | **3/6** | 0.9710 | ✅ 已收口 | 精确任务为 1、3、5 |
| ExtendToBoundary | 冻结 7B 边界下现实上界 2/6 | **2/6** | 0.9376 | ✅ 已收口 | 精确任务为 2、4；1/3/5/6 转记 Step 3 |
| ExtractObjects | ≥2/6 | **2/6** | 0.5887 | ✅ 已收口 | 精确任务为 1、3 |
| CleanUp | 冻结未收口能力缺口 | **0/6** | 0.9248 | ✅ 已冻结 | 保留为未收口能力缺口，不计入当前已收口组 |

### 4.2 全量 36 任务回归快照

为确认 Step 2b 没有破坏前序结果，本轮同时回跑全部 36 个训练任务。总体结果如下：

1. 总任务数：36。
2. 精确求解数：15。
3. 分组结果：Copy 2/6，Center 6/6，MoveToBoundary 3/6，ExtendToBoundary 2/6，ExtractObjects 2/6，CleanUp 0/6。
4. 失败归因分布：`NONE = 15`，`ABSTRACTION_FAIL = 21`。
5. 最常被选中的分割方案：`bg_fg`。
6. 最常被选中的对齐策略：`bipartite`。

这个结果说明 Step 2b 已经把新增四组压到当前冻结边界下的稳定状态，但它并没有改变 Step 2a 仍为 **8/12** 的事实。因此，Step 2b 验收通过并不自动等于 Step 2 整体完成。

### 4.3 回归与诊断状态

本轮验收最重要的工程性结果之一，是已知成功样例没有被后续阶段破坏：

1. [regression_flags.json](phase1/outputs/phase9_full/reports/regression_flags.json) 为空。
2. Step 2a 成功样例（Copy1、Copy2、Center1-6）无回归。
3. MoveToBoundary 已成功样例（1、3、5）无回归。
4. ExtendToBoundary 冻结边界内成功样例（2、4）无回归。
5. ExtractObjects 已成功样例（1、3）无回归。

同时，Phase 8 新增的诊断字段已经稳定落盘，可用于后续 Step 3 继续接手：

1. `bg_color`。
2. 每个 segmentation plan 的对象面积分布。
3. `noise_objects.threshold`。
4. `noise_objects.selected_ids` 与 `selected_count`。

### 4.4 性能数据

Phase 9 全量回归的平均各层耗时如下：

| 层 | 平均耗时 (ms) |
|----|-------------|
| Layer 1 | 4.889 |
| Layer 2 | 29.611 |
| Layer 3 | 12.750 |
| Layer 4 | 23.806 |
| Layer 5 | 0.000 |

这些数据与 Step 2b 主要新增的候选枚举、方向解析与报告落盘复杂度相匹配，没有出现不可接受的预算失控。

## 5. 验收结果

### 5.1 Step 2b 验收决策

**Step 2b 按当前冻结口径验收通过。**

通过依据如下：

1. MoveToBoundary 达到 **3/6**，满足组级最低门槛。
2. ExtendToBoundary 已按冻结 7B 边界完成收口，现实上界 **2/6** 已被实测确认，且边界外任务已诚实转记 Step 3。
3. ExtractObjects 达到 **2/6**，满足组级最低门槛。
4. CleanUp 已完成真实基线诊断、原型验证和冻结决策，后续不再伪装成“即将达标”的在界问题。
5. Phase 8 的 runner、报告、回归标记和诊断产物已具备真实语义并通过实跑验证。
6. 全量 36 任务回归无已知成功样例回退。

### 5.2 需要明确的不通过项

Step 2b 的通过 **不等于** Step 2 整体已经完成。本轮报告同时确认：

1. Step 2a 仍为 **8/12**，未达到 Step 2 整体验收要求中的 **≥9/12** 原始硬门槛。
2. 因此，当前最准确的项目状态是“Step 2b 已验收，Step 2 整体未最终收口”。
3. Step 2a 未达门槛所对应的剩余能力缺口，已经正式归因为 Step 3 能力，而不是继续回流到 Step 2b 处理。

## 6. 测试状态

```text
$ python3 -m unittest discover -s phase1/tests/step2 -p "test_*.py"
Ran 104 tests in 8.927s

OK
```

当前测试覆盖 Layer 1-5、runner、概念组报告、回归标记、ExtendToBoundary 新参数边界、以及任务级诊断输出。与 Step 2a 报告中的 78 tests 相比，新增覆盖的主要是 Step 2b 的原语扩展、keepalive、选择器约束和 Phase 8 报告链路。

## 7. 交付产物

| 产物 | 路径 | 说明 |
|------|------|------|
| 源代码 | `phase1/src/step2/` | Step 2 独立实现，未修改 `phase1/src/step1/` |
| 单元测试 | `phase1/tests/step2/` | 104 tests, 0 failures |
| 全量报告 | `phase1/outputs/phase9_full/reports/summary.json` | 36 任务聚合摘要 |
| 全量报告 | `phase1/outputs/phase9_full/reports/summary.md` | 可读版摘要 |
| 回归标记 | `phase1/outputs/phase9_full/reports/regression_flags.json` | 已知成功样例回归检测 |
| 逐任务归因 | `phase1/outputs/phase9_full/reports/attributions.json` | 逐任务归因详情 |
| 调试产物 | `phase1/outputs/phase9_full/debug/` | 每任务调试输出，含诊断字段 |
| 设计文档 | `phase1/docs/step2/Step2实现设计-0v1.md` | 已同步全量回归与收口判断 |
| 任务清单 | `phase1/docs/step2/Step2实现任务分解清单-0v1.md` | 已同步 Phase 7A-9 状态 |
| 验收报告 | `phase1/docs/step2/Step2b实验与验收报告-0v1.md` | 本报告 |

## 8. 结论

Step 2b 当前最合理的定位，是“在冻结边界下已完成验收的增量扩展阶段”，而不是“需要继续补丁追求名义全过”的开放施工阶段。MoveToBoundary、ExtendToBoundary、ExtractObjects 三组已经在当前边界内稳定收口，CleanUp 也已经通过真实实验被诚实地冻结为未收口能力缺口；与此同时，Phase 8 基础设施把这些判断变成了可重复、可审计的批量报告流程。

因此，本报告给出的正式阶段性结论是：截至 2026-04-06，**Step 2b 已验收通过**，其余遗留问题应按现有文档口径转交 Step 3 处理；但 **Step 2 整体仍不能宣告完成**，因为 Step 2a 的原始硬门槛仍未满足。