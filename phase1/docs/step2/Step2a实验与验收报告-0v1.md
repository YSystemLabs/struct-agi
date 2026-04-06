# 第一阶段 Step 2a 实验与验收报告

> 版本：v0.1
>
> 状态：已验收（有条件通过）
>
> 日期：2026-04-05
>
> 作用：汇总 Step 2a 的实验设置、关键结果、与设计预测的偏差、以及验收结论。

## 1. 实验目标与范围

Step 2a 的目标是在 Step 1 最小闭环基础上，通过引入 `bg_fg` 分割方案、前/背景动态渲染、`largest_object` / `center_object` 等语义选择器，将 ConceptARC Copy + Center 12 个训练任务的精确求解数从 6/12 提升至 ≥9/12。

Step 2a 不引入 MoveToBoundary、ExtendToBoundary、ExtractObjects、CleanUp 等新概念组——这些属于 Step 2b 范围。

## 2. 实验设置

本次实验使用 [Step2实现设计-0v1.md](Step2实现设计-0v1.md)、[Step2最小接口与任务清单附录-0v1.md](Step2最小接口与任务清单附录-0v1.md) 和 [Step2实现任务分解清单-0v1.md](Step2实现任务分解清单-0v1.md) 作为设计边界。实现采用 Python 标准库与 unittest，不使用第三方依赖、隐藏缓存或随机性。

Step 2 运行配置如下：

1. 分割方案扩展为 cc4、cc8、whole_grid、**bg_fg**。
2. 原语范围在 Step 1 基础上新增 extend_to_boundary。
3. 关系范围新增 containment（包含关系）。
4. Layer 3 beam 大小：`STEP2_BEAM_SIZE = 64`。
5. 新增语义一致性打分：copy +0.35，delete / translate / crop 各 +0.15，用于降低语义合理候选被 beam 误截断的概率。
6. 新增 per-pixel 颜色追踪（`pixel_colors`），解决多色连通组件的渲染丢色问题。

## 3. 关键实现与偏差记录

### 3.1 原设计预测 vs 实际修复路径

设计文档 §4 对 6 个失败任务逐一做了根因诊断和修复预案。以下记录实际偏差：

| 任务 | 设计预测的修复路径 | 实际修复路径 | 偏差说明 |
|------|-------------------|-------------|---------|
| Copy2 | bg_fg + recolor + selector | **pixel_colors 基础设施** | 设计预测为 bg_fg 中心定位 + 语义选择器；实际根因是 cc4 下多色对象渲染只用单一颜色，需要贯穿 build→transform→render 全链路的 per-pixel color 追踪 |
| Center3 | bg_fg + crop = center_object | **bg_fg 输出回退 + same_color CC + crop 语义 bonus**（三层联合修复） | 设计预测方向正确（bg_fg + crop），但未预见需要输出端 bg_fg → cc4 回退、以及 beam 排序中 crop 需要 semantic bonus 才能存活 |
| Copy3 | anchor-relative translate（低信心） | ❌ 不可解 | 与设计的低信心预测一致，需要参数化位移 |
| Copy4 | anchor-relative translate（低信心） | ❌ 不可解 | 同上 |
| Copy5 | repeat/tile（低信心） | ❌ 不可解 | 与设计预测一致，需输出尺寸变换 |
| Copy6 | repeat/tile（低信心） | ❌ 不可解 | 与设计预测一致，需输出尺寸变换 |

### 3.2 代码变更清单

按实施顺序排列：

1. **scoring.py**: `pre_priority` 新增 `mode=` 计入 attr_ref_count；新增 copy (+0.35) 与 delete / translate / crop（各 +0.15）语义一致性 bonus。
2. **task_runner.py**: bg_fg 输出回退——当输出端 bg_fg 提取到 0 个前景对象时，回退到 cc4 分割。
3. **objects.py**: `extract_cc_objects` 新增 `same_color: bool = False` 参数；bg_fg 场景使用 `same_color=True`，确保背景扣除后的前景连通组件不因颜色差异过度分裂。
4. **perception.py**: bg_fg 调用链使用 `same_color=True`。
5. **models.py**: `ObjectData` 新增 `pixel_colors: dict[Cell, int] = field(default_factory=dict)`。
6. **objects.py**: `build_object` 和 `build_whole_grid_object` 填充 pixel_colors。
7. **executor.py**: 所有变换操作（translate、rotate、flip、recolor、fill、crop、extend\_to\_boundary、delete\_center\_component 等）全链路传播 pixel_colors。新增 `_rotate_once_with_colors`、`_flip_pixels_with_colors` 辅助函数。
8. **render.py**: `render_objects` 使用 `obj.pixel_colors.get((row, col), default_color)` 实现 per-pixel 颜色渲染。
9. **test_layer1.py**: Schema 断言新增 `pixel_colors` 字段。
10. **test_layer3.py**: 更新 pre_priority 期望值。

## 4. 实验结果

### 4.1 核心指标（Copy + Center 原始 12 任务）

| 任务 | Step 1 结果 | Step 2a 结果 | 像素精度 | 选中方案 | 选中程序 |
|------|-----------|-------------|---------|---------|---------|
| Copy1 | ✅ 100% | ✅ 100% | 1.000 | cc4 | copy→translate(dx=input_width) |
| Copy2 | ❌ 0% | **✅ 100%** | 1.000 | cc4 | copy(smallest)→translate(to_largest_center) |
| Copy3 | ❌ | ❌ | 0.937 | whole_grid | crop(center_object) |
| Copy4 | ❌ | ❌ | 0.837 | whole_grid | crop(center_object) |
| Copy5 | ❌ | ❌ | 0.370 | cc4 | crop(cc4:0) |
| Copy6 | ❌ | ❌ | 0.437 | bg_fg | copy(largest_object) |
| Center1 | ✅ 100% | ✅ 100% | 1.000 | bg_fg | fill(center_cell) |
| Center2 | ✅ 100% | ✅ 100% | 1.000 | bg_fg | crop(center_object) |
| Center3 | ❌ 2.1% | **✅ 100%** | 1.000 | bg_fg | crop(center_object) |
| Center4 | ✅ 100% | ✅ 100% | 1.000 | cc4 | delete(input_center_component) |
| Center5 | ✅ 100% | ✅ 100% | 1.000 | cc4 | translate(rare_motif_to_center) |
| Center6 | ✅ 100% | ✅ 100% | 1.000 | bg_fg | translate(rare_motif_to_center) |

**求解总数：8/12（基线 6/12 → +2: Center3, Copy2）**

### 4.2 扩展概念组（Step 2b 范围，仅作基线记录）

| 概念组 | 求解数 | 说明 |
|--------|-------|------|
| MoveToBoundary | 0/6 | 最高 94.4%（MTB6），需 extend_to_boundary + directional semantics |
| ExtendToBoundary | 0/6 | 最高 96.9%（ETB2），需方向性延伸语义 |
| ExtractObjects | 2/6 | **EO1=100%, EO3=100%**；现有 DSL 恰好能表达这两个任务 |
| CleanUp | 0/6 | 最高 95.4%（CU3），需噪声识别与删除 |

注意：ExtractObjects1 和 ExtractObjects3 在未做任何 Step 2b 特定优化的情况下即可求解，说明当前 DSL 表达力已部分覆盖更复杂的概念组。

### 4.3 失败归因分布

- NONE（精确求解）：10
- ABSTRACTION_FAIL（DSL 表达力不足）：26

所有未解任务均归因为 ABSTRACTION_FAIL，无 PERCEPTION_FAIL（感知不足）、SELECTION_FAIL（选择失败）或 EXECUTION_FAIL（执行失败）。这一分布支持“当前批次的主要瓶颈集中在 DSL 表达力侧”这一判断，但它本身不单独构成“可表达范围内链路稳定”的严格证明；更强结论仍需结合逐任务调试产物审查。当前 26 个未解任务的 `failure_detail` 均非空，且记录了最佳像素精度（如 `best_pixel_accuracy=0.9369`），满足交付检查表中对 failure detail 可追溯性的要求。

### 4.4 性能数据

| 层 | 平均耗时 (ms) |
|----|-------------|
| Layer 1 | 4.7 |
| Layer 2 | 14.2 |
| Layer 3 | 10.0 |
| Layer 4 | 22.8 |
| Layer 5 | 0.0 |

全部 36 个任务的端到端批量运行在数秒内完成。

## 5. 与正式门槛的偏差处理

设计文档 §6 规定 Step 2a 正式门槛为 **≥9/12 且基线不回归**。实际结果为 **8/12**，未达门槛。

### 5.1 偏差原因

4 个未解任务（Copy3/4/5/6）的失败根因已通过逐任务可行性验证附录获得可审计支撑，详见 [Step2a-Copy3-6可行性验证附录-0v1.md](Step2a-Copy3-6可行性验证附录-0v1.md) 与 `phase1/outputs/step2/reports/copy3_6_feasibility_audit.json`：

- **Copy3/4**：在附录定义的“单对象复制 + 常数平移 + 原画布叠加”两套穷举家族（same-color cc4 / 非零前景 cc4）中，不存在能跨训练对精确成立的共享参数组合；最佳位移在 pair 间不一致，支持“当前 DSL 至少缺少 pair-invariant 的参数化位移语义”这一判断。
- **Copy5/6**：训练对逐 pair 要求输出尺寸扩张，并表现为沿单轴的重复展开。附录给出了逐 pair 的输入/输出尺寸表；当前 DSL 无 repeat / tile / construct_grid 原语，因此现有 Step 2 程序族缺少与该结构直接对应的构造能力。

这些限制是 **架构级**的，无法通过调参、权重调整或样例特判修复。当前项目决策是不在 Step 2 阶段内扩边界修复，而是把它们登记为 **Step 3 提前引入能力**：Copy3/4 对应参数化 anchor-relative 位移语义，Copy5/6 对应 repeat / tile / construct_grid 一类构造语义。

### 5.2 验收决策

基于以下理由，建议 **有条件通过** Step 2a 验收：

1. **基线完整无回归**：Step 1 的 6 个求解任务全部保持 100%。
2. **新增求解与设计方向一致**：Center3（bg_fg + crop）、Copy2（pixel_colors + translate to center）均在设计意图范围内，非 ad hoc 特判。
3. **失败归因诚实且可审计**：4 个未解任务已有独立附录和 JSON 审计结果支撑，结论落点收敛为“超出当前 Step 2 程序族的可表达范围”，不是“差一点就能过”的调参问题。
4. **设计文档已预见低信心**：§4.7 明确标注 Copy3-6 修复信心为"低"，并预留了"若改善不足应诚实归因"的回退口径。
5. **意外收益**：ExtractObjects1/3 在无专门优化下即求解，表明 DSL 扩展已部分溢出设计预期。

**有条件通过的约束**：Step 2b 不因 Copy3-6 扩边界；相关能力需求应在设计文档中登记为 Step 3 提前引入能力，作为后续阶段的明确输入。

## 6. 测试状态

```
$ python3 -m unittest discover -s phase1/tests/step2 -p "test_*.py"
Ran 78 tests in 7.4s — OK
```

测试覆盖 Layer 1-5、runner、接口冻结与 beam/ID 行为。相比 Step 1（71 tests），新增 7 个测试覆盖 bg_fg 分割、pixel_colors 传播、语义选择器等 Step 2 新增能力。

## 7. 交付产物

| 产物 | 路径 | 说明 |
|------|------|------|
| 源代码 | `phase1/src/step2/` | 独立于 Step 1，未修改 `phase1/src/step1/` |
| 单元测试 | `phase1/tests/step2/` | 78 tests, 0 failures |
| 批量报告 | `phase1/outputs/step2/reports/summary.json` | 36 任务聚合指标 |
| 批量报告 | `phase1/outputs/step2/reports/summary.md` | 可读摘要 |
| 归因文件 | `phase1/outputs/step2/reports/attributions.json` | 逐任务归因详情 |
| 可行性审计 | `phase1/outputs/step2/reports/copy3_6_feasibility_audit.json` | Copy3-6 逐任务验证结果（机器可读） |
| 调试产物 | `phase1/outputs/step2/debug/` | 每任务 layer1-5 中间输出 |
| 设计文档 | `phase1/docs/step2/Step2实现设计-0v1.md` | 已标注实施结果 |
| 任务清单 | `phase1/docs/step2/Step2实现任务分解清单-0v1.md` | 已标注 Phase 完成状态 |
| 验证附录 | `phase1/docs/step2/Step2a-Copy3-6可行性验证附录-0v1.md` | Copy3-6 可行性验证说明与结果解释 |

## 8. 验收结论

**Step 2a 按"有条件通过"验收。**

通过依据：

1. 端到端闭环可复现：36 个任务可批量运行并输出完整调试产物、Attribution 和汇总报告。
2. 求解率从 6/12 提升至 8/12，新增 Copy2 和 Center3 两个求解任务。
3. 基线 6 个任务全部保持 100%，无回归。
4. 4 个未达任务已通过附录化可行性验证交付物支撑为当前 Step 2 程序族缺口，非简单调参可修复。
5. 全部 78 个单元测试通过，无跳过或 expected failure。
6. 扩展概念组额外求解 ExtractObjects1/3，总计 10/36。
7. 所有未解任务归因为 ABSTRACTION_FAIL，归因链路完整。

有条件约束：

- 8/12 未满足 ≥9/12 正式门槛，但偏差原因（DSL 表达力上限）已明确记录，不应通过样例级特判强行拉升。
- Step 2b 不承接 Copy3-6 的边界外修复；相关能力需求应登记为 Step 3 提前引入能力（parametric offset、repeat/tile / construct_grid）。
