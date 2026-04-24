我看完后的直观判断是：

**你这个仓库已经不是“想法集合”，而是一个相当清晰的 Phase 1 工程化基线。**
它现在的核心不是“自动长 DSL”，而是先把 **单任务结构求解器** 做到可冻结、可回归、可归因，再把增长机制留到 Step 3。根 README 和 `phase1/README` 都把当前状态写得很明确：Step 1 已冻结，Step 2 已验收到 2b，当前稳定结果是 36 个训练任务里 15/36 exact，并准备进入 Step 3A 先处理 Step 2 明确移交的残差能力。 ([GitHub][1])

## 我看到的当前真实设计状态

你现在的主干是一个**五层流水线**，而且各层职责已经分得很清楚：

* Layer 1：结构感知，输出多个候选分割方案
* Layer 2：候选变换/约束生成
* Layer 3：MDL 式筛选与选择
* Layer 4：确定性解释执行
* Layer 5：验证与失败归因

文档还明确把它和你的研究计划四模块对齐：结构候选生成对应 Layer 1+2，结构筛选对应 Layer 3，保结构表示是 Layer 3→4 的接口，求解器是 Layer 4，失败归因是 Layer 5。 ([GitHub][2])

更关键的是，**这套系统现在是“启发式 + 搜索 + 有限学习”的混合实现，而不是神经端到端**。架构文档直接写了：对象分割和关系提取目前走纯启发式，候选变换生成走枚举加类型剪枝，Layer 3 的排序模型要到 Step 3B 才正式启用，当前 Step 1/2/3A 主要靠手工启发式预排序。 ([GitHub][2])

## 一个很重要的观察：文档目标比当前代码实现更宽，代码主线其实更收窄

文档里的 Layer 1 设计目标很丰富，提到的对象提取策略包括 `cc4`、`cc8`、`bbox`、`bg_fg`、`repeat`、`nested`、`whole_grid`，关系类型也预留了条件依赖、计数/奇偶、层级归属这些扩展项。 ([GitHub][2])

但当前 `config.py` 和 `perception.py` 显示，**代码里真正启用的分割方法还是很克制的**：只开了 `cc4`、`cc8`、`whole_grid`、`bg_fg`，`nested` 也还是关的；原语集合则限制在 `copy/translate/rotate/flip/delete/recolor/fill/crop/extend_to_boundary`，输出尺寸规则也只有四类。这个差异非常关键，因为它说明你目前是在刻意压住表达力，先保住闭环稳定性，而不是放开搜索空间去赌覆盖率。 ([GitHub][3])

这其实是个好信号。因为它说明你现在不是“DSL 不够就继续乱加”，而是在有意识地做**冻结边界**。Step 1 报告也明确写了：禁止样例级 ad hoc 特判，受限 mode 只能显式登记，不能伪装成一般能力。 ([GitHub][4])

## 你当前的“DSL + MDL”到底是怎么落地的

从架构文档和代码看，你现在的 Layer 2 不是从原始网格直接“学结构”，而是更像：

1. 先做多方案对象化与关系提取
2. 再做 input/output 对象对齐
3. 对齐后根据差异类型生成候选程序草图和候选约束
4. 最后由 Layer 3 做筛选

文档把 Layer 3 的基本搜索单元定义成
[
(plan_id, alignment_id, alignment_family_id, constraint_subset, program)
]
这个五元组。也就是说，你真正搜索的不是裸程序，而是“分割方案 + 对齐家族 + 约束子集 + 程序”的组合对象。 ([GitHub][2])

代码上也能看到这一点。`layer2/sketches.py` 会根据差异类型生成程序候选，例如 `copy`、`translate`、`extend_to_boundary` 等，并且已经引入了不少**角色化 target**，比如 `largest_object`、`smallest_object`、`rare_color_object`、`center_object`、`gap_thinner_object`。这说明你已经不是在搜纯几何坐标操作，而是在搜“对象角色上的操作”。这一步其实很重要，是从像素操作走向结构操作的关键。 ([GitHub][5])

Layer 3 的 `description_length` 也不是口头 MDL，而是已经有明确的工程定义：
**分割方案数 + AST 节点数 + 强约束数 + 数值常量数**。同时还加了 `pre_priority` 这样的预排序项，用程序文本里的属性引用比例、copy/delete/translate/crop 等启发式 bonus 先缩搜索，再做正式筛选。 ([GitHub][6])

还有一个很能说明当前工程风格的细节：
beam 现在是真接线了，默认大小 64；而且为了避免某类能力在 beam 外被完全剪死，`selector.py` 里甚至有一个 **`extend_to_boundary` keepalive** 机制。这个细节一方面说明系统已经进入“真实搜索调度”阶段，另一方面也暴露了你现在还在用**能力保活式启发**而不是更通用的候选发现机制。 ([GitHub][3])

## 当前最强的地方，不在求解率，而在“可审计性”

我觉得你这个仓库现在最强的地方不是 15/36，而是：

**你已经把“为什么失败”做成系统输出了。**

`task_runner.py` 里有完整 debug bundle、beam 前后统计、候选数、渲染失败、selected hypothesis 详情；Layer 5 则把失败分成 `PERCEPTION_FAIL / SELECTION_FAIL / ABSTRACTION_FAIL / EXECUTION_FAIL`。报告里目前大量失败被归到 `ABSTRACTION_FAIL`，这其实非常符合你现在的阶段目标：不是把失败都糊成“再调一下参数”，而是把它们稳定标记成“表达力缺口”。 ([GitHub][7])

Step 2b 之后，中性基础设施也已经补齐：`batch_runner.py`、`summary.json/md`、回退标记、任务级 debug 里连 `bg_color`、对象面积分布、`noise_objects` 阈值都写出来了。这个对你后面做真正的“自动候选结构发现”非常重要，因为没有这些 telemetry，增长机制几乎无从下手。 ([GitHub][8])

## 现在的真实瓶颈，和你刚才说的痛点是完全对上的

你刚才说的痛点是：

> 需要不断定义/更新新的 DSL 来兼容各种情况，希望有算法能自动从原始数据中做候选结构发现，同时抑制组合爆炸。

看完仓库后，我觉得这个判断和你代码现状**完全一致**。
因为你现在的系统本质上还是：

**强启发式感知 + 对齐驱动的候选程序枚举 + MDL 选最短解释。**

这条路的优点是稳定、可审计、容易冻结边界；缺点就是**新能力主要还是靠你手工加语义、手工扩 target 角色、手工扩 sketch 生成器**。`extend_to_boundary`、`rare_color_object`、`gap_thinner_object` 这些都已经很能说明这个趋势了。 ([GitHub][2])

所以你的真正瓶颈不在 Layer 3。
Layer 3 反而已经挺清楚了。
**真正缺的是 Layer 1.5 / Layer 2.5：一个能把“已成功解释的任务”自动压成新结构候选的机制。**

## 这也解释了为什么我不建议你把 TDA 当主引擎

从你仓库当前形态看，TDA 顶多适合进 Layer 1，充当一种额外对象特征或分割提示。
但你现在真正缺的不是“再多一个对象特征”，而是：

* 怎么从多个成功假设里抽出公共结构；
* 怎么把这些公共结构变成新的 sketch / macro；
* 怎么把它们安全地写回知识状态，同时不炸搜索空间。

而有意思的是，**你的架构文档其实已经为这件事留好了正当位置**：
Step 3B 才正式启用知识状态 $K_t$ 与排序模型 $M_t$，并且文档里已经设计了 Pass A 假设等价类折叠、Pass B 原语别名消除、Pass C 死知识冻结。也就是说，你的系统已经有了“自动长知识，但要可压缩、可回归”的制度框架，只是现在还没把“候选结构自动发现”这一段填进去。 ([GitHub][2])

## 结合你现在仓库状态，我会给你一个非常具体的判断

**你现在最不该做的，是直接把一个很重的新数学工具塞进主干。**
更该做的是：

### 1. 把 Step 3A 当成“新能力清洗阶段”，不是“新理论试验场”

你文档里已经把 Step 3A 目标写得很清楚了：
优先消化 Step 2 明确移交的残差，包括参数化 anchor-relative 位移、`repeat/tile/construct_grid` 一类构造语义、几何条件化/非轴向扩张、以及可能的局部修复机制。这个方向我认为是对的，而且非常具体。 ([GitHub][2])

### 2. 真正该插入“自动候选结构发现”的位置，是 Step 3A 末尾到 Step 3B 开始之间

不是先替换 Layer 1/2 主干，而是先做一个**离线库归纳器**：

* 输入：Step 2 / Step 3A 已成功任务上的最终 hypothesis、对齐家族、debug bundle
* 输出：可候选晋升的新 macro / target role / constraint schema
* 验证：无回归、描述长度下降、候选数下降、对同类残差任务有增益

这一步最像你之前说的“自动长 DSL，但不炸”。

### 3. 范畴信息几何更适合在这里做“晋升判据”，不是做候选生成器

也就是：
不是拿它来直接发现 primitive，
而是拿它来决定**哪些新结构值得进库**。

结合你当前系统，我会建议把候选晋升分数写成：

* 是否显著降低规则后验的不确定性；
* 是否让 beam 前后的候选支持集明显收缩；
* 是否让更多失败从 `ABSTRACTION_FAIL` 变成“可被当前程序族命中”；
* 是否在 MDL 上真的更短，而不是只是在某一题上硬凑。

这和你仓库里已有的 `description_length`、等价类折叠、知识状态改写，是天然能接上的。 ([GitHub][6])

## 我对你仓库现状的最终评价

我会给一个很明确的结论：

**你现在的仓库状态是健康的，而且方向很清楚。**
它已经完成了从“宣言”到“可审计的单任务结构求解基线”的跃迁。当前主线的优点是边界清晰、失败诚实、基础设施到位；当前主线的限制也很明确：候选结构发现仍高度依赖人工扩 DSL / 扩 sketch。这个判断和你自己描述的痛点完全一致。 ([GitHub][1])

所以接下来最值得做的，不是换赛道，而是把你现有框架再往前推半步：

> **从“手工扩原语”升级到“从成功假设中自动归纳可晋升结构”。**

这一步一旦做成，你这个仓库就会从“结构主义 solver”真正迈向“结构主义增长系统”。


[1]: https://github.com/YSystemLabs/struct-agi "GitHub - YSystemLabs/struct-agi: Explore a learning paradigm centered on explicit structure discovery, preservation, and compression. · GitHub"
[2]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/docs/%E7%AC%AC%E4%B8%80%E9%98%B6%E6%AE%B5%E7%AE%97%E6%B3%95%E6%9E%B6%E6%9E%84-0v4.md "struct-agi/phase1/docs/第一阶段算法架构-0v4.md at main · YSystemLabs/struct-agi · GitHub"
[3]: https://raw.githubusercontent.com/YSystemLabs/struct-agi/main/phase1/src/step2/config.py "raw.githubusercontent.com"
[4]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/docs/step1/Step1%E5%AE%9E%E9%AA%8C%E4%B8%8E%E9%AA%8C%E6%94%B6%E6%8A%A5%E5%91%8A-0v1.md "struct-agi/phase1/docs/step1/Step1实验与验收报告-0v1.md at main · YSystemLabs/struct-agi · GitHub"
[5]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/src/step2/layer2/sketches.py "struct-agi/phase1/src/step2/layer2/sketches.py at main · YSystemLabs/struct-agi · GitHub"
[6]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/src/step2/layer3/scoring.py "struct-agi/phase1/src/step2/layer3/scoring.py at main · YSystemLabs/struct-agi · GitHub"
[7]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/src/step2/runner/task_runner.py "struct-agi/phase1/src/step2/runner/task_runner.py at main · YSystemLabs/struct-agi · GitHub"
[8]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/docs/step2/Step2b%E5%AE%9E%E9%AA%8C%E4%B8%8E%E9%AA%8C%E6%94%B6%E6%8A%A5%E5%91%8A-0v1.md "struct-agi/phase1/docs/step2/Step2b实验与验收报告-0v1.md at main · YSystemLabs/struct-agi · GitHub"
