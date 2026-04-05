# Step 2a Copy3-6 可行性验证附录

> 版本：v0.1
>
> 状态：与 Step 2a 验收报告配套
>
> 日期：2026-04-05
>
> 作用：把 Step 2a 主报告中关于 Copy3-6 的“可行性验证”落成可复查、可比对、可追溯的交付物。

## 1. 附录定位

本附录不改变 [Step2a实验与验收报告-0v1.md](Step2a实验与验收报告-0v1.md) 的主结论，只把其中“Copy3-6 超出当前 Step 2 程序族可表达范围”的判断补成可审计证据链。

附录依赖以下现有产物：

1. 原始任务文件：`phase1/datasets/raw/ConceptARC/corpus/Copy/Copy3.json` 至 `Copy6.json`
2. 当前批量运行归因：`phase1/outputs/step2/reports/attributions.json`
3. 当前批量汇总：`phase1/outputs/step2/reports/summary.json`
4. 本附录对应的机器可读审计文件：`phase1/outputs/step2/reports/copy3_6_feasibility_audit.json`

## 2. 验证边界

本附录做的是“当前 Step 2 程序族必要性检查”，不是对“所有可能 DSL 扩展”的不可能性证明。

口径严格限定如下：

1. 对 Copy3 / Copy4，验证目标是：当前 Step 2 最接近的候选家族“单对象复制 + 常数平移 + 原画布叠加”是否存在跨训练对共享的精确参数。
2. 对 Copy5 / Copy6，验证目标是：训练对是否已经直接要求输出尺寸扩张与重复展开；若是，则当前缺少 repeat / tile / construct_grid 原语的 Step 2 程序族为何没有对应构造能力。
3. 因此，本附录支持的结论是“超出当前 Step 2 程序族的可表达范围”，而不是“数学上绝对不可解”。

## 3. 方法

### 3.1 Copy3 / Copy4：常数平移复制家族穷举

对每个 train pair，分别在两种对象切分口径下做穷举：

1. same-color cc4：仅把同色且 4 连通的前景像素聚成对象。
2. nonzero cc4：把所有非零且 4 连通的前景像素聚成对象，不区分颜色，但在复制时保留原像素颜色。

穷举空间定义如下：

1. 对输入网格中的每个候选对象逐一枚举。
2. 在 `dx ∈ [-W, W]`、`dy ∈ [-H, H]` 范围内穷举所有常数位移。
3. 候选程序语义固定为：复制该对象，并将复制体以 `(dx, dy)` 平移后叠加回原画布；超出画布边界的像素丢弃。
4. 以像素级精确匹配率为评分，记录每个 train pair 的最优结果以及是否存在精确解。
5. 最后检查：是否存在同一组 `(对象编号, dx, dy)` 能在同一任务的所有 train pair 上同时达到 100%。

这个检查不能覆盖 anchor-relative、参数化位移等更强语义；它的作用是给出一个严格、可复跑的上界：若连该家族都不存在跨 pair 共享精确解，则“靠调 beam / 调权重把当前家族补到 100%”的说法缺少证据。

### 3.2 Copy5 / Copy6：尺寸扩张与重复展开检查

对 Copy5 / Copy6，不再做“常数平移复制”穷举主审计，而是记录更直接的必要性证据：

1. 逐 train pair 比对输入 / 输出网格尺寸。
2. 标记输出是否沿单轴发生尺寸增长。
3. 结合训练样本直接观察输出结构是否表现为“主图样重复展开，中间插入 0 分隔带”。

该检查的判断目标不是“当前实现为什么只得到 37.0% / 43.7%”，而是“任务本身是否已经要求 Step 2 之外的构造能力”。

## 4. 结果

### 4.1 Copy3 / Copy4 穷举结果

| 任务 | Pair | same-color cc4 最优 | nonzero cc4 最优 | 是否存在该 pair 的精确解 | 跨 pair 共享精确参数 |
| --- | --- | --- | --- | --- | --- |
| Copy3 | 0 | acc=0.9432, comp=6, dx=7, dy=0 | acc=0.9545, comp=5, dx=7, dy=0 | 否 | 否 |
| Copy3 | 1 | acc=0.9795, comp=1, dx=6, dy=3 | acc=0.9949, comp=1, dx=6, dy=3 | 否 | 否 |
| Copy4 | 0 | acc=0.9040, comp=0, dx=16, dy=0 | acc=0.9040, comp=0, dx=16, dy=0 | 否 | 否 |
| Copy4 | 1 | acc=0.9152, comp=2, dx=6, dy=9 | acc=0.9330, comp=2, dx=6, dy=9 | 否 | 否 |

可直接得出的结论只有两条：

1. 在上述两套“单对象复制 + 常数平移 + 原画布叠加”家族中，Copy3 / Copy4 都不存在 train-pair 级别的精确解，更不存在跨 pair 共享的精确参数。
2. 两个任务的最优位移在不同 pair 上不一致，因此“存在一个当前 DSL 已经可表达的常量平移程序，只是 beam 没搜到”这一说法没有被附录支持。

这不足以单独证明“唯一正确扩展就是 anchor-relative parametric displacement”，但它确实支持更弱、也更严谨的结论：**当前 Step 2 程序族缺少跨 pair 保持一致的位移语义。**

### 4.2 Copy5 / Copy6 尺寸检查结果

| 任务 | Pair | 输入尺寸 | 输出尺寸 | 直接观测 |
| --- | --- | --- | --- | --- |
| Copy5 | 0 | 4x5 | 4x9 | 水平扩张，输出为主图样重复展开 |
| Copy5 | 1 | 3x5 | 3x11 | 水平扩张，输出为主图样多次重复展开 |
| Copy5 | 2 | 6x4 | 15x4 | 垂直扩张，输出为主图样沿纵轴重复展开 |
| Copy6 | 0 | 3x11 | 7x11 | 垂直扩张，输出为主图样沿纵轴重复展开 |
| Copy6 | 1 | 9x4 | 9x9 | 水平扩张，输出为主图样沿横轴重复展开 |

这一组证据说明：Copy5 / Copy6 的训练对本身就要求输出画布沿单轴增长，并把已有图样以 repeat / tile 形式展开。当前 Step 2 代码库虽然允许 copy / translate / crop / fill / recolor / extend_to_boundary 等原语组合，但没有显式的 repeat / tile / construct_grid 原语，也没有按计数规则多次构造新画布的语义接口。

因此，本附录对 Copy5 / Copy6 给出的判断是：**问题不在阈值或 beam，而在当前 Step 2 程序族缺少直接对应的构造能力。**

### 4.3 与当前批量归因文件对齐

当前 `attributions.json` 中 4 个任务的结果如下：

| 任务 | 当前选中方案 | 当前选中程序 | 当前像素精度 | failure_type | failure_detail |
| --- | --- | --- | --- | --- | --- |
| Copy3 | whole_grid | `crop[target=center_object,mode=tight_bbox]` | 0.9369 | ABSTRACTION_FAIL | `best_pixel_accuracy=0.9369` |
| Copy4 | whole_grid | `crop[target=center_object,mode=tight_bbox]` | 0.8371 | ABSTRACTION_FAIL | `best_pixel_accuracy=0.8371` |
| Copy5 | cc4 | `crop[target=cc4:0,mode=tight_bbox]` | 0.3704 | ABSTRACTION_FAIL | `best_pixel_accuracy=0.3704` |
| Copy6 | bg_fg | `copy[target=largest_object] ; on_copy: ; on_original:` | 0.4365 | ABSTRACTION_FAIL | `best_pixel_accuracy=0.4365` |

附录的作用不是覆盖这些归因，而是把“为什么这 4 个任务不应被表述为调参残差”补成可复查证据。

## 5. 结论落点

结合主报告与本附录，较严谨的结论应写成：

1. Copy3 / Copy4：当前 Step 2 已审计的常数平移复制家族不存在跨 pair 共享精确解，支持把后续扩展方向落在更强位移语义上。
2. Copy5 / Copy6：训练对直接要求尺寸扩张与重复展开，支持把后续扩展方向落在 repeat / tile / construct_grid 这一类构造原语上。
3. 因而，Copy3-6 继续停留在 Step 2a 的“调 beam / 调 bonus / 调排序”层面，缺少证据表明能获得质变。
4. 项目记录口径上，这四项能力不回写为 Step 2b 范围，而是登记为 Step 3 提前引入能力：Copy3 / Copy4 对应参数化 anchor-relative 位移，Copy5 / Copy6 对应 repeat / tile / construct_grid。

## 6. 配套交付物

本附录对应的机器可读结果保存在：`phase1/outputs/step2/reports/copy3_6_feasibility_audit.json`

推荐把主报告中的“穷举确认”统一理解为：**已有独立附录和机器可读审计文件支撑的、限定于当前 Step 2 程序族的必要性检查结果。**

同时，推荐把主报告中的相关后续处理表述具体理解为：**正式登记为 Step 3 提前引入能力，而不是回流到 Step 2b 扩边界实现。**