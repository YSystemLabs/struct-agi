对，而且这两个诉求其实应该合并成一个答案：

> **范畴信息几何不太像“再给你几个新原语”，它更像一套“什么结构值得被发现、保留、晋升”的判据。**
> 真正的自动候选结构发现，则应该是一个独立机制；范畴信息几何负责给这个机制定方向、定预算、定准入。

你现在仓库的主干已经很适合这样接：项目本身就是五层闭环，强调可审计中间结构、知识状态 $K_t$ 的渐进增长，以及“扩展后必须重写”而不是只做规则堆积；当前也已经进入 Step 3A 准备阶段。([GitHub][1])

## 先回答第一个：范畴信息几何能带来什么新洞见

我的判断是：**能，而且是“约束算法设计”的洞见，不是“替你发明 primitive”的洞见。**

### 1. 它会逼你把 solver 看成“后验收缩系统”，而不是“程序枚举器”

你现在的架构已经天然适合这样看：Layer 1 出多方案对象图，Layer 2 出候选变换和约束，Layer 3 选最小充分结构子集，Layer 5 做失败归因。文档里还明确写了：系统不是每题从零开始，而是维护一个可增长、可重写的知识状态。([GitHub][2])

这时候范畴信息几何最有价值的翻译是：

* Layer 1 的职责不是“多提一些对象”，而是**把对任务有用的信息显式化**
* Layer 2 的职责不是“多生一些程序”，而是**提出能显著收缩规则后验的候选**
* Layer 3 的职责不是“找最短程序”，而是**找最小但充分的结构子集**
* Layer 5 的职责不是“报错”，而是**定位哪一层没有完成应有的信息收缩**

也就是说，你的系统目标应该从：

> 找一个能过样例的程序

改成：

> 在每层都尽量把与任务无关的不确定性压掉，只保留后续求解必须的信息。

这就是我觉得范畴信息几何最适合给你的第一条指导。

### 2. 它会给“新结构能不能进库”一个比 MDL 更强的准则

你现在 Layer 3 的 `description_length` 已经很清晰：分割方案数 + AST 节点数 + 强约束数 + 常量数；同时还有 `pre_priority`，会偏好属性引用、copy/delete/translate/crop 这类更“语义一致”的程序。([GitHub][3])

这很好，但还不够。

我建议你把“候选结构晋升”为新 primitive / 新 selector / 新关系类型的条件，改成三条同时满足：

1. **后验收缩**
   它是否显著降低了规则假设的不确定性。
   也就是：加入这个结构后，候选支持集有没有明显缩小。

2. **任务充分性**
   它是否保住了解题真正需要的信息，而不是只在训练 pair 上碰巧 fit。
   这对应“保结构”的本意。

3. **可分解性提升**
   它是否让原来缠在一起的问题更接近分层、条件独立、局部可验证。
   这会直接减少后续组合爆炸。

所以你可以把现在“MDL 最短即可”的想法，升级成：

$$
\mathrm{Promote}(s) \propto
\frac{\Delta_{\mathrm{posterior\_shrink}} + \Delta_{\mathrm{task\_sufficiency}} + \Delta_{\mathrm{decomposability}}}
{\Delta_{\mathrm{desc\_length}} + \Delta_{\mathrm{search\_branching}}}
$$

其中分子三项分别表示“后验收缩 / 任务充分性 / 可分解性”的增量，分母两项分别表示“描述长度 / 搜索分支”的增量。

这不是现成论文公式，而是我认为最适合你系统的范畴信息几何翻译。

### 3. 它会把“组合爆炸控制”从句法预算改成信息预算

你现在已经有很强的复杂度意识：文档里对扩展准入直接规定了，新原语引入的组合数增量不能超过当前总候选数的 20%；同时只有达到最小触发频次、且不破坏已解任务的扩展才能通过。([GitHub][2])

这是很对的。
但还可以再往前走一步：

不要只问“新增 primitive 会让搜索树大多少”，还要问：

* 它是否在**更早层**就完成了足够的信息收缩
* 它是否把一个原本需要深搜索的问题，变成了浅层可判别的问题
* 它是否让后面的 beam 不再靠 keepalive 硬保活

这里你代码里其实已经暴露出痛点了：sketch 生成器里已经出现了很多手工角色化 target，比如 `rare_color_object`、`gap_thinner_object`。这说明系统正在通过“新增语义角色”来人为压缩搜索，而不是让这些角色自己长出来。([GitHub][4])

所以范畴信息几何给你的第三条设计指导是：

> **优先奖励“早收缩”的结构，而不是“晚补救”的结构。**

越早让候选空间塌缩的结构，越值得升格。

---

## 再回答第二个：怎样把手工扩原语做成自动候选结构发现

我的结论很明确：

> **不要把“自动候选结构发现”做成在线搜题时的一部分。**
> **把它做成阶段间的离线增长器。**

这和你当前架构天然兼容。因为你的文档已经把增长机制写好了：Layer 5 会产生 `expansion_hint`，Step 3B 以后会有知识状态扩展、扩展准入、以及三阶段知识重写。([GitHub][2])

也就是说，你真正该补的不是主求解器，而是：

## 一个“候选结构归纳器”

输入不是原始网格本身，而是你系统已经产出的高价值中间物：

* 成功 hypothesis
* alignment family
* constraint subset
* debug bundle
* 失败归因
* beam 前后存活候选
* 选中的 symbolic parameter

这一步特别重要，因为你现在已经不是没有信号，而是**信号很多，但还没被组织成增长机制**。

### 我建议的自动化路线

#### A. 固定一个小而稳的 core DSL

不要继续频繁手改底层原语集合。
你当前 Step 2 的原语集合本来就很克制：`copy / translate / rotate / flip / delete / recolor / fill / crop / extend_to_boundary`。([GitHub][5])

这个 core DSL 应该尽量稳定，因为：

* core 越稳，自动增长出的东西越容易评估
* core 越稳，等价类折叠和回归验证才有意义
* core 越稳，新增结构更容易被理解为“宏/模式/选择器”，而不是底层语义污染

#### B. 自动发现的对象，不是先长 primitive，而是先长三类“中间结构”

第一类：**selector / role**
也就是现在你手工写进去的那些：

* rare_color_object
* center_object
* largest_object
* gap_thinner_object

它们很像原语，但其实更应该被看成：
**对象图上的可复用角色谓词**。

自动化办法是：
从成功任务里统计“被选中对象”的稳定属性模式，做反统一，得到 selector schema，例如：

* 最稀有颜色且面积最小
* 与最大对象中心最近
* 填补两对象间唯一狭缝
* 唯一满足某关系链的对象

你不是直接长一个新 primitive，而是长一个：

$$
\text{Selector}(o) := \phi(\text{attrs}(o), \text{relations}(o,\cdot))
$$

第二类：**constraint schema**
你现在已经有强约束/弱约束和失败归因。下一步不是多加 if，而是自动发现哪些约束总是成组出现，例如：

* 颜色映射一致 + 计数守恒
* 相对位置不变 + 输出尺寸规则固定
* 某类对象单调扩张 + 另一类对象不变

这些 schema 很适合进入 Layer 3，作为比单条约束更高阶的筛选器。

第三类：**macro / sketch pattern**
这才是最接近“自动长 DSL”的部分。
做法不是直接从原始网格长程序，而是从**已成功程序**里长宏。

举例说，你如果经常看到这类程序片段反复出现：

* 选某角色对象 → 平移到某 anchor
* copy → on_copy 执行 translate/fill
* 先 crop 某 bbox → 再 recolor / fill

那就对这些成功片段做反统一，抽出公共 skeleton，然后作为 macro candidate。

#### C. 用“反统一”而不是“多加特征”来做候选生成

你现在真正缺的是这个操作。

你已经有很多成功 hypothesis 和部分失败但很接近的 hypothesis。
最自然的自动增长机制不是 TDA，而是：

1. 从成功任务里抽出最终程序、对象角色、约束组合
2. 对它们做**反统一**
3. 得到公共模板
4. 把模板参数化成 macro / selector / relation schema
5. 再让 MDL + 信息准则决定是否升格

这一步的核心思想很简单：

> **新结构不是拍脑袋发明，而是从已有成功解释中压缩出来。**

这和你整个项目“结构发现—筛选—保持”的哲学是完全一致的。

#### D. 用“等价折叠”抑制增长后的爆炸

你的文档里已经有 Pass A 假设等价类折叠、Pass B 别名消除、Pass C 死知识冻结。([GitHub][2])

这意味着你已经意识到：

> 增长如果只有加法，没有重写，一定会退化成规则堆积。

所以自动候选结构发现一旦开始，必须和等价折叠一起上线。
否则你会从“手工扩原语”变成“自动堆原语”，本质没变。

我建议实际实现时强制执行这条：

* 每个新候选进入候选库前，先做 canonicalization
* 凡是行为等价、只是在表面参数命名或局部顺序上不同的，先合并
* 真正晋升的只能是**带来压缩**的候选，而不是只是“多一个说法”

---

## 把两件事合起来，你就会得到一个很清楚的改造方向

### 范畴信息几何负责：

* 定义什么叫“好结构”
* 定义什么叫“早收缩”
* 定义什么叫“值得升格”
* 定义哪一层该承担哪种不确定性的消解

### 自动候选结构发现负责：

* 从成功解释和失败归因中提出新 selector / constraint schema / macro
* 做反统一与等价折叠
* 用 MDL + 信息准则筛选
* 通过扩展准入和回归验证写回 $K_t$

---

## 我给你的具体建议，不是大改架构，而是加一个模块

直接在 Step 3A / 3B 之间插入一个新模块：

## Structure Miner v0.1

输入：

* `selected_program`
* `selected_alignment_family`
* `selected_constraints`
* `failure_type / failure_detail / expansion_hint`
* beam 前后候选集
* train pair 上的对象角色命中记录

输出：

* selector candidates
* constraint schema candidates
* macro candidates
* candidate equivalence classes
* promotion scores

评分标准：

* 跨任务支持度
* 后验收缩增益
* 输出不确定性下降
* 搜索分支增量
* 描述长度变化
* 回归安全性

准入标准：

* 至少命中 $k$ 个不同任务
* 对 `solved_task_set_stage` 不回归
* 搜索空间增量在预算内
* 可被三阶段重写吸收

---

## 最后给一个非常明确的结论

**一，范畴信息几何能给你真实指导，但主要体现在“结构晋升标准”和“分层信息职责”上。**
它最适合告诉你：什么是值得保留的抽象，什么是早收缩，什么是合法的中间表示。

**二，手工扩原语要自动化，最现实的路线不是找一个万能新数学工具，而是：**
**成功解释反统一 → 生成 selector / macro / constraint schema → 等价折叠 → MDL + 信息准则筛选 → 通过准入后写回知识状态。**

**三，TDA 最多是 Layer 1 的局部传感器，不是你这条主问题的核心答案。**
你真正缺的，是一个“从已成功结构里自动压出新结构”的增长器，而不是再多一个特征提取器。

[1]: https://raw.githubusercontent.com/YSystemLabs/struct-agi/main/README.md "raw.githubusercontent.com"
[2]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/docs/%E7%AC%AC%E4%B8%80%E9%98%B6%E6%AE%B5%E7%AE%97%E6%B3%95%E6%9E%B6%E6%9E%84-0v4.md "struct-agi/phase1/docs/第一阶段算法架构-0v4.md at main · YSystemLabs/struct-agi · GitHub"
[3]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/src/step2/layer3/scoring.py "struct-agi/phase1/src/step2/layer3/scoring.py at main · YSystemLabs/struct-agi · GitHub"
[4]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/src/step2/layer2/sketches.py "struct-agi/phase1/src/step2/layer2/sketches.py at main · YSystemLabs/struct-agi · GitHub"
[5]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/src/step2/config.py "struct-agi/phase1/src/step2/config.py at main · YSystemLabs/struct-agi · GitHub"
