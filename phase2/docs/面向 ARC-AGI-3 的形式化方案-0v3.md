# 面向 ARC-AGI-3 的形式化方案

> 版本：v0.3
>
> 状态：草案
>
> 定位：不追求最一般的数学优雅，而是：**尽量准确贴住 ARC-AGI-3 的真实接口与难点，并能直接落成 agent 架构。**

ARC-AGI-3 是交互式、turn-based 的 benchmark，代理通过标准动作接口与 2D 网格环境循环交互；要在没有显式说明书的情况下探索环境、推断目标、建立内部模型并规划动作。评分用 RHAE，既看完成度也看相对人类动作效率，只有真正作用到环境的动作计分，内部推理和工具调用不计入动作。([docs.arcprize.org][1])

## 一、v0.3 的总结构

我建议把系统写成四层复合结构：

$$
\mathcal H_E \xrightarrow{C_K} \mathcal I \xleftarrow{\Pi} \mathcal B_{\text{task}} \xleftarrow{p} \mathcal E
$$

其中：

* $\mathcal H_E$：交互历史层
* $\mathcal I$：信息状态层
* $\mathcal B_{\text{task}}$：任务语境层
* $\mathcal E$：任务条件化的结构/模型/计划层

这比单层 $p:\mathcal E\to\mathcal B$ 更适合 AGI-3，因为 benchmark 真正给你的不是“任务语义”，而是 frames、actions、以及动作后的新 frame；代理首先面对的是历史压缩与状态抽象，然后才是任务解释、结构提升和规划。官方文档也把 benchmark 的核心能力写成 Exploration、Percept→Plan→Action、Memory、Goal Acquisition。([docs.arcprize.org][2])

---

## 二、形式化定义

### 2.1 环境与动作

固定未知环境 $E$。它提供观测序列和标准动作接口。每一步代理接收 1–N 个 JSON frames，并返回一个动作。官方动作集合包括 `RESET`、`ACTION1`–`ACTION5`、带 $(x,y)$ 的 `ACTION6`，以及 `ACTION7=Undo`；游戏进入 game-over 后，唯一合法动作是 `RESET`。([docs.arcprize.org][1])

记：

$$
\mathcal O = \text{观测空间},\qquad
\mathcal A = \text{动作空间},\qquad
\mathcal T = \text{终局状态集合}
$$

---

### 2.2 历史层 $\mathcal H_E$

定义历史：

$$
h_t = (o_0,a_0,o_1,\dots,a_{t-1},o_t)
$$

其中 $o_i\in\mathcal O, a_i\in\mathcal A$。

定义范畴 $\mathcal H_E$：

* 对象：所有有限合法历史 $h_t$
* 态射：一步扩展
   $h_t \to h_{t+1}$

这层只记录“真实发生了什么”。

---

### 2.3 信息状态层 $\mathcal I$

定义压缩映射：

$$
C_K:\mathcal H_E\to\mathcal I
$$

它依赖长期知识库 $K$。对任意历史 $h_t$，定义：

$$
i_t = C_K(h_t)
$$

其中

$$
i_t=
(\mathsf{Obj}_t,\mathsf{Evt}_t,\mathsf{Inv}_t,\mathsf{Aff}_t,\mathsf{Mem}_t,\mathsf{Graph}_t)
$$

含义如下：

* $\mathsf{Obj}_t$：对象化候选或对象分布
* $\mathsf{Evt}_t$：动作—结果事件摘要
* $\mathsf{Inv}_t$：当前已发现不变量/约束
* $\mathsf{Aff}_t$：候选 affordances
* $\mathsf{Mem}_t$：压缩后的历史索引
* $\mathsf{Graph}_t$：状态—动作探索图

其中 $\mathsf{Graph}_t$ 建议显式写成：

$$
\mathsf{Graph}_t=(V_t,E_t,F_t,U_t)
$$

* $V_t$：已访问抽象状态
* $E_t$：已验证转移
* $F_t$：frontier，尚待验证的状态-动作边
* $U_t$：undo / reversible 结构摘要

这层是 AGI-3 的底座，因为上下文预算有限，而环境又是交互式的，必须做 history compression 和 state abstraction。官方技术报告明确把 context management、从长历史中提取 relevant state、以及 uncertainty 下的高效规划列为核心难点。([ARC Prize][3])

定义信息更新态射：

$$
\iota_t:i_t\to i_{t+1}
$$

表示一次

$$
(\text{act},\text{observe},\text{compress})
$$

之后的信息状态更新。

---

### 2.4 任务语境层 $\mathcal B_{\text{task}}$

保留你原来方案里最有价值的部分，但把它放在信息状态之上。

一个任务语境对象定义为：

$$
b=(G_b,P_b,R_b,H_b)
$$

其中：

* $G_b$：候选目标语义
* $P_b$：候选进展语义
* $R_b$：相关性准则
* $H_b$：历史视界/解释时间尺度

但 $b$ 不是直接从外部给定，而是由当前信息状态诱导出来。定义任务提议映射：

$$
\Pi(i_t)\subseteq \mathrm{Ob}(\mathcal B_{\text{task}})
$$

并在其上维护后验：

$$
\mu_t \in \Delta(\Pi(i_t)),\qquad
\mu_t(b)=\Pr(b\mid i_t)
$$

所以“在线提出任务”被形式化为：
**基于信息状态 $i_t$，维护任务语境后验 $\mu_t$。**

任务层态射保留你原来的方向：

$$
u:b'\to b
$$

表示 $b'$ 是 $b$ 的细化/具体化。这样可以自然得到后面的重索引。这个方向对于“从模糊任务解释逐渐收缩为更具体解释”是合适的，也符合 AGI-3 里通过探索不断细化目标理解的过程。技术报告明确说代理必须自己 infer goals、build internal models、plan effective actions。([ARC Prize][3])

---

### 2.5 结构层 $p:\mathcal E\to\mathcal B_{\text{task}}$

对每个任务语境 $b$，定义纤维 $\mathcal E_b$。

一个纤维对象定义为：

$$
e=(O_e,Rel_e,Dyn_e,Sch_e;\ g_e,m_e,\pi_e,w_e,\delta_e)
$$

其中：

* $O_e$：对象化方式
* $Rel_e$：关系结构
* $Dyn_e$：局部动力学/转移规律
* $Sch_e$：子目标/策略骨架
* $g_e$：绑定的目标解释
* $m_e$：绑定的世界模型
* $\pi_e$：导出的局部计划
* $w_e$：权重/后验/MDL 分数
* $\delta_e$：诊断与反例痕迹

这个定义比单纯的“结构对象”更适合 AGI-3，因为 benchmark 同时要求探索、目标推断、建模与规划。把 $(g,m,\pi)$ 绑进同一个对象，算法上会更稳。([ARC Prize][3])

---

## 三、核心算子

### 3.1 任务后验更新

定义：

$$
\mu_{t+1}(b)\propto \mu_t(b)\cdot \mathrm{Lik}(o_{t+1}\mid i_t,a_t,b)
$$

并允许：

* 新增任务语境候选
* 细化现有语境
* 合并近似语境
* 淘汰明显矛盾语境

---

### 3.2 结构发现算子

对高权重任务语境 $b$，定义：

$$
D_b^t:(i_t,X_b^t,K_t)\to \mathcal P_{\mathrm{fin}}(\mathrm{Ob}(\mathcal E_b))
$$

它负责：

* propose
* refine
* split
* merge
* elevate-seed

这里 $X_b^t$ 是当前 $b$ 下活跃候选池。

---

### 3.3 联合筛选算子

保留你的 joint score / joint MDL。

$$
\mathrm{Score}_t(b,e)=
\mathrm{Fit}_t(b,e)
-\lambda L_{\mathcal B}(b)
-\gamma L_{\mathcal E}(e\mid b)
+\beta \mathrm{VOI}_t(b,e)
$$

或者

$$
\mathrm{MDL}_t(b,e)=
L_{\mathcal B}(b)+L_{\mathcal E}(e\mid b)+L_{\mathrm{res}}(h_t\mid b,e)
$$

这里：

* $\mathrm{Fit}$：对已观测历史的解释力
* $L_{\mathcal B}$：任务语境复杂度
* $L_{\mathcal E}$：结构复杂度
* $\mathrm{VOI}$：继续验证该候选的区分价值

这一步很重要，因为 AGI-3 的动作成本直接进入评分，任务解释和结构解释都必须节制复杂度。RHAE 对动作效率敏感，所以不能只追求解释力，不顾验证成本。([docs.arcprize.org][4])

---

### 3.4 结构保持式提升

保留你的核心定义：

$$
A_b:\mathcal E_b^{\mathrm{sel}}\to \mathcal T_b
$$

它把筛选后的低层结构提升为高层任务对象，例如：

* 子目标图
* 策略骨架
* 任务级不变量
* 可复用高层 affordance 模板

这里 (A_b) 回答的是：
**哪些低层结构值得被抬升为真正指导规划的高层对象。**

---

### 3.5 语义重写

同样保留你的区分：

$$
N_b:\mathcal E_b\to \overline{\mathcal E}_b
$$

要求：

$$
Q_b(N_b(e))=Q_b(e)
$$

其中 $Q_b$ 是当前任务语境下的参考语义测试族。

这一步负责：

* 折叠等价候选
* 去别名
* 冻结死知识
* 选规范代表

它和你 `struct-agi` 里的“三阶段改写”是直接对应的。

---

### 3.6 重索引

对任务层态射 $u:b'\to b$，定义：

$$
u^*:\mathcal E_b\to\mathcal E_{b'}
$$

它表示：
粗语境下筛出的结构，在更细语境里如何被重新解释、保留、降权或淘汰。

v0.3 里先只保留 $u^*$。
$\Sigma_u\dashv u^*$ 这类 pushforward/伴随结构，先降级成以后要逼近的性质，不作为当前最小实现的硬要求。

---

## 四、动作选择

这是 v0.3 的核心落地部分。

### 4.1 probe / exploit 双模态

定义动作策略：

$$
a_t=
\begin{cases}
a_t^{\text{probe}} & \text{if uncertainty high} \\
a_t^{\text{exploit}} & \text{if dominant hypothesis stable}
\end{cases}
$$

其中：

* `probe`：优先做可证伪实验
* `exploit`：优先执行当前高置信计划

---

### 4.2 动作效用

定义：

$$
a_t=\operatorname{arg\,max}_{a\in\mathcal A(i_t)} J(a\mid i_t,\mu_t,{X_b^t})
$$

其中

$$
J=
\lambda_{\text{solve}}V_{\text{solve}}
+\lambda_{\text{falsify}}V_{\text{falsify}}
+\lambda_{\text{frontier}}V_{\text{frontier}}
-\lambda_{\text{cost}}c
-\lambda_{\text{risk}}r
$$

解释：

* $V_{\text{solve}}$：对当前主导目标假设的推进价值
* $V_{\text{falsify}}$：预期淘汰错误假设的价值
* $V_{\text{frontier}}$：图前沿探索价值
* $c$：动作成本
* $r$：风险，包括不可逆性、game-over 风险、长 undo 距离

之所以把 $V_{\text{falsify}}$ 单列，是因为 AGI-3 的难点不只是 planning，还包括 hypothesis revision；技术报告明确把 exploration strategy 和 planning under uncertainty 作为当前系统差距所在。([ARC Prize][3])

此外，官方动作接口里存在 `Undo`，这意味着“可撤销探测动作”和“高风险不可逆动作”价值不同，所以把 reversible / irreversible 纳入 $r(a)$ 是合理的。([docs.arcprize.org][5])

---

## 五、两时间尺度与多 level 记忆

ARC-AGI-3 的分数按 game 聚合，并且 level 分数按 level index 加权；更高 level 权重更大。官方评分方法说明了 per-level score、per-game aggregation 和 total score 的计算方式。([docs.arcprize.org][4])

因此 v0.3 应显式区分三层记忆：

$$
\Sigma_{g,\ell,t}=(K,\ m_g,\ i_{g,\ell,t},\ \mu_{g,\ell,t},\ X_{g,\ell,t})
$$

其中：

* $K$：跨 game 长期知识
* $m_g$：同一 game 内跨 level mechanics memory
* $i_{g,\ell,t}$：当前 level 的信息状态
* $\mu_{g,\ell,t}$：当前任务语境后验
* $X_{g,\ell,t}$：当前活跃结构候选池

这样分是因为 AGI-3 不是孤立单题；在同一 game 内，前面 level 学到的 mechanics 可能迁移到后面 level，而评分又对后面 level 更敏感。([docs.arcprize.org][4])

---

## 六、最小算法框架

下面是可以直接落成代码模块的最小 loop。

### 6.1 初始化

$$
i_0=C_K(h_0),\qquad
\mu_0=\mathrm{InitTaskPosterior}(i_0),\qquad
X_b^0=\varnothing
$$

如果是同一 game 的后续 level，则从 $m_g$ warm-start。

---

### 6.2 主循环

对每一步 $t$：

1. **压缩历史**：$i_t=C_K(h_t)$

1. **更新任务后验**：$\mu_t=\mathrm{UpdateTaskPosterior}(i_t,\mu_{t-1})$

1. **在高权重任务语境上发现结构**：对所有 $b$ with $\mu_t(b)$ 高于阈值，调用 $X_b^t \leftarrow D_b^t(i_t,X_b^{t-1},K)$。

1. **联合筛选**：对 $(b,e)$ 计算 joint score / joint MDL，并保留 beam 内候选。

1. **结构保持式提升**：$T_b^t=A_b(X_b^{t,\mathrm{sel}})$

1. **语义重写**：$X_b^t \leftarrow N_b(X_b^t)$

1. **选择动作**：先判定当前属于 probe 还是 exploit，再用 $J(a)$ 选动作。

1. **执行动作并更新历史**：$h_{t+1}=h_t\cdot a_t \cdot o_{t+1}$

1. **终止判断**：若当前 level 到达终局，则退出 level loop。

---

### 6.3 level 结束后

更新同 game 记忆：

$$
m_g \leftarrow \mathrm{ConsolidateLevel}(m_g,{i_t,\mu_t,X_t}_{t})
$$

---

### 6.4 game 结束后

更新长期知识：

$$
K \leftarrow R\bigl(K\sqcup \Delta K_g\bigr)
$$

其中 $R$ 是你的长期重写算子。

---

## 七、失败归因

v0.3 建议至少保留下面几类错误：

`PERCEPTION_FAIL`, `TASK_FAIL`, `MODEL_FAIL`, `LIFT_FAIL`, `REWRITE_FAIL`, `PROBE_FAIL`, `PLAN_FAIL`, `EXECUTION_FAIL`

其中：

* `PERCEPTION_FAIL`：对象化/事件抽取错
* `TASK_FAIL`：任务语境后验没覆盖真解释
* `MODEL_FAIL`：动力学假设错
* `LIFT_FAIL`：该提升的结构没被抬升
* `REWRITE_FAIL`：规范化误删有用结构
* `PROBE_FAIL`：实验动作没有有效区分假设
* `PLAN_FAIL`：目标和模型对，但计划错
* `EXECUTION_FAIL`：动作合法性/调用流程错

---

## 八、删减后的实现原则

为了让 v0.3 真正可跑，我建议保留以下工程约束：

1. **有限活跃任务语境集**
   不做无限 $\mathcal B_{\text{task}}$，只保留 top-k 任务语境。

2. **有限 beam 的结构候选池**
   不做一般范畴对象集，只保留 beam 内候选。

3. **伴随结构先不实现**
   $\Sigma_u\dashv u^*$ 先作为未来目标。

4. **任务语境先做小而硬的 schema 库**
   特别是 $(G_b,P_b)$ 不要一开始太自由。

5. **对象化必须允许不确定性**
   $(\mathsf{Obj}_t,\mathsf{Evt}_t)$ 不要默认单值。

---

## 九、最简总结

把 v0.3 压成一句话就是：

> history compression → information state → task-context posterior → task-conditioned structure discovery → lift → rewrite → probe/exploit action selection

我认为这版已经比 v0.2 更适合直接指导算法设计，因为它明确补上了：

* 同 game 跨 level 记忆
* 状态—动作探索图
* probe / exploit 双模态
* 可逆性进入动作价值
* 感知不确定性作为一等对象

[1]: https://docs.arcprize.org/games?utm_source=chatgpt.com "Games - ARC-AGI-3 Docs"
[2]: https://docs.arcprize.org/?utm_source=chatgpt.com "ARC-AGI-3 Quickstart - ARC-AGI-3 Docs"
[3]: https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf?utm_source=chatgpt.com "arXiv:submit/7403127 [cs.AI] 24 Mar 2026"
[4]: https://docs.arcprize.org/methodology?utm_source=chatgpt.com "ARC-AGI-3 Scoring Methodology"
[5]: https://docs.arcprize.org/actions?utm_source=chatgpt.com "Actions - ARC-AGI-3 Docs"
