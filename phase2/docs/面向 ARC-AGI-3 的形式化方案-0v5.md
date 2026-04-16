# 面向 ARC-AGI-3 的形式化方案

> 版本：v0.5
>
> 状态：草案
>
> 定位：在 v0.3 / v0.4 的骨架上，显式加入 Markov 范畴信息几何语义，使形式化不仅描述“结构发现—筛选—保持”，也描述“信息如何通过交互通道被获取、压缩、更新与复用”。

---

现有 v0.3 已经把 ARC-AGI-3 建成了四层结构：历史层、信息状态层、任务语境层、任务条件化结构层；v0.4 又在信息层和结构层显式引入了候选池、激活子集、缓存，以及 `LazySelect / Force` 的惰性调度机制。与此同时，ARC-AGI-3 官方本身就是 interactive、turn-based、强调 exploration、percept→plan→action、memory、goal acquisition 的 benchmark，这正适合用“随机通道持续复合更新”的语言来写。([GitHub][1])

## 0. 设计原则

v0.5 保持 v0.3 / v0.4 的主结构不变：

$$
\mathcal H_E \xrightarrow{C_K} \mathcal I \xleftarrow{\Pi} \mathcal B_{\text{task}} \xleftarrow{p} \mathcal E
$$

其中：

* $\mathcal H_E$：交互历史层
* $\mathcal I$：信息状态层
* $\mathcal B_{\text{task}}$：任务语境层
* $\mathcal E$：任务条件化的结构/模型/计划层

v0.5 新增的核心原则有四条：

### 0.1 通道原则

ARC-AGI-3 的本体不是静态输入输出映射，而是：

* agent 内部状态
* 动作选择
* 环境反馈
* 观测更新
* 多回合复合

因此，v0.5 要把关键更新过程显式写成**随机通道 / 过程核**，而不只写成抽象“更新规则”。这和 ARC-AGI-3 官方把 benchmark 定义为 turn-based、action-response cycle、要求探索未知环境并在线获得目标与模型的设定一致。([ARC Prize Docs][2])

### 0.2 信息收缩原则

系统的目标不再只是“找到一个能解释当前历史的程序/结构”，而是：

> 在动作成本与计算预算约束下，尽快收缩与任务无关的不确定性，并保留对未来决策真正有用的信息。

因此：

* 好的对象化，不只是能分出对象，而是能减少未来歧义
* 好的任务语境，不只是 fit 观测，而是能稳定预测未来反馈
* 好的结构候选，不只是解释当前历史，而是能支撑后续行动
* 好的动作，不只是推进目标，也可能是在主动获取信息

### 0.3 惰性仍然只是调度，不是不确定性的本体

延续 v0.4：

* 不确定性仍由候选族 + 权重/后验 + 未定约束来表示
* 惰性只决定哪些候选现在展开，哪些继续悬置
* 需要通过与环境交互获取的信息，不能被内部惰性求值替代

### 0.4 合法抽象原则

一个结构候选之所以值得提升，不只是因为它更短，而是因为它对未来观测、目标推进、动作排序而言是**近似充分**的。

也就是说：

> 抽象不是任意压缩；抽象必须尽量不损伤未来信息处理能力。

---

## 1. 总结构：从四层链条到“通道复合的四层链条”

v0.5 仍采用四层链条：

$$
\mathcal H_E \xrightarrow{C_K} \mathcal I \xleftarrow{\Pi} \mathcal B_{\text{task}} \xleftarrow{p} \mathcal E
$$

但额外显式引入三个通道层面的对象：

* 环境隐藏状态空间 $S$
* 动作空间 $\mathcal A$
* 观测空间 $\mathcal O$

并定义环境通道：

$$
T_{\mathrm{env}} : S_t \otimes A_t \rightsquigarrow O_{t+1} \otimes S_{t+1}
$$

这里 $\rightsquigarrow$ 表示一般随机过程或通道，不要求是单值确定映射。

这样，ARC-AGI-3 的一步交互就被写成：

$$
b_t \xrightarrow{\pi_t} a_t \xrightarrow{T_{\mathrm{env}}} o_{t+1} \xrightarrow{U_t} b_{t+1}
$$

其中 $b_t$ 在这里不是“任务语境对象”，而是 agent 的广义内部 belief state；在本方案中，它将由 $(i_t,\mu_t,X_t)$ 联合承担。

---

## 2. 历史层 $\mathcal H_E$：真实交互轨迹

历史定义保持 v0.3 / v0.4 不变：

$$
h_t = (o_0, a_0, o_1, \dots, a_{t-1}, o_t)
$$

定义范畴 $\mathcal H_E$：

* 对象：所有有限合法历史 $h_t$
* 态射：一步扩展 $h_t \to h_{t+1}$

这一层仍然只是“真实发生了什么”的记录层，不引入惰性。

但 v0.5 明确指出：
历史扩展不是纯句法追加，而是由环境通道诱导：

$$
h_{t+1} = h_t \cdot a_t \cdot o_{t+1},
\qquad
o_{t+1} \sim T_{\mathrm{env}}(s_t, a_t)
$$

因此，历史层是**环境随机过程的可见轨迹层**。

---

## 3. 信息状态层 $\mathcal I$：belief construction 与惰性候选池

### 3.1 总体定义

沿用 v0.4 的候选族写法：

$$
i_t =
(\Omega_t^{obj}, \Omega_t^{evt}, \mathsf{Inv}_t, \mathsf{Aff}_t, \mathsf{Mem}_t, \mathsf{Graph}_t, \Lambda_t)
$$

其中：

* $\Omega_t^{obj}$：对象化候选池
* $\Omega_t^{evt}$：事件解释候选池
* $\mathsf{Inv}_t$：当前约束/不变量
* $\mathsf{Aff}_t$：当前 affordance 候选
* $\mathsf{Mem}_t$：压缩历史索引
* $\mathsf{Graph}_t$：状态—动作探索图
* $\Lambda_t$：惰性调度状态

### 3.2 把 $C_K$ 升级为 belief construction channel

v0.3 / v0.4 写：

$$
i_t = C_K(h_t)
$$

v0.5 中保留这个记法，但把 $C_K$ 的语义提升为：

$$
C_K : \mathcal H_E \rightsquigarrow \mathcal I
$$

即：它不再只是“压缩函数”，而是**belief construction / state abstraction 通道**。

这样做的原因是：

* 对象化不是单值事实，而是候选族
* 事件解释不是单值事实，而是候选族
* 未来规划依赖的是“当前 belief 中保留了什么”，而不是“历史本身”

因此，$C_K$ 的职责不是重建全部历史，而是尽量构造一个对未来交互近似充分的信息状态。

### 3.3 信息状态的近似充分性

v0.5 显式加入如下设计目标：

$$
D\!\bigl(
P(O_{t+1}, G_{t+1} \mid h_t, a_t)
\,\|\,
P(O_{t+1}, G_{t+1} \mid i_t, a_t)
\bigr)
\le \varepsilon_I
$$

其中：

* $G_{t+1}$ 表示目标推进或任务相关反馈
* $D$ 是选定的 divergence
* $\varepsilon_I$ 是允许的信息损失

含义是：

> 好的信息状态 $i_t$ 应该是对历史 $h_t$ 的近似充分压缩。

这条准则会在后面直接指导：

* 哪些对象化值得展开
* 哪些记忆值得保留
* 哪些历史可以忘掉

---

## 4. 任务语境层 $\mathcal B_{\text{task}}$：任务后验是可更新的 belief

### 4.1 任务语境对象

沿用 v0.3：

$$
b = (G_b, P_b, R_b, H_b)
$$

其中：

* $G_b$：候选目标语义
* $P_b$：候选进展语义
* $R_b$：相关性准则
* $H_b$：历史视界/解释尺度

并由信息状态诱导：

$$
\Pi(i_t) \subseteq \mathrm{Ob}(\mathcal B_{\text{task}})
$$

维护后验：

$$
\mu_t \in \Delta(\Pi(i_t)),
\qquad
\mu_t(b) = \Pr(b \mid i_t)
$$

### 4.2 任务后验更新作为显式通道

v0.3 / v0.4 中已有：

$$
\mu_{t+1}(b) \propto \mu_t(b) \cdot \mathrm{Lik}(o_{t+1} \mid i_t, a_t, b)
$$

v0.5 把它提升为显式更新通道：

$$
U_{\text{task}} :
(\mu_t, i_t, a_t, o_{t+1}) \rightsquigarrow \mu_{t+1}
$$

其核心语义是：

* 用新观测更新任务语境后验
* 合并相近任务解释
* 淘汰与新证据矛盾的任务解释
* 必要时引入新的任务语境候选

### 4.3 probe 动作的第一信息目标

对任务层，v0.5 显式定义 probe 的首要信息目标为：

$$
a_t^{\text{probe-task}}
=
\operatorname{arg\,max}_a
\mathbb{E}\left[
H(\mu_t) - H(\mu_{t+1})
\mid i_t, \mu_t, a
\right]
$$

或者等价写成：

$$
a_t^{\text{probe-task}}
=
\operatorname{arg\,max}_a I(B; O_{t+1} \mid i_t, a)
$$

其中 $B$ 是任务语境随机变量。

也就是说：

> probe 动作首先应该优先区分任务解释，而不是盲目试探。

---

## 5. 结构层 $p:\mathcal E \to \mathcal B_{\text{task}}$：结构候选、预测通道与提升

### 5.1 纤维对象

沿用 v0.3 / v0.4：

$$
e =
(O_e, Rel_e, Dyn_e, Sch_e;\ g_e, m_e, \pi_e, w_e, \delta_e)
$$

其中：

* $O_e$：对象化方式
* $Rel_e$：关系结构
* $Dyn_e$：局部动力学
* $Sch_e$：子目标或策略骨架
* $g_e$：绑定目标解释
* $m_e$：绑定模型
* $\pi_e$：局部计划
* $w_e$：权重或后验或复杂度
* $\delta_e$：诊断与反例痕迹

### 5.2 惰性结构候选池

保持 v0.4：

$$
X_b^t = (\mathcal C_{b,t}^{str}, w_{b,t}^{str}, A_{b,t}^{str}, Z_{b,t}^{str})
$$

其中：

* $\mathcal C_{b,t}^{str}$：结构候选集合
* $w_{b,t}^{str}$：候选权重
* $A_{b,t}^{str}$：已激活并真正展开的结构候选
* $Z_{b,t}^{str}$：共享缓存与可复用中间结果

### 5.3 新增：预测通道 $\Phi_{b,e}$

这是 v0.5 的关键新增对象。

对每个任务语境 $b$ 与结构候选 $e$，定义预测通道：

$$
\Phi_{b,e} :
(i_t, a_t)
\rightsquigarrow
\Delta(O_{t+1}, G_{t+1}, R_{t+1})
$$

其中：

* $O_{t+1}$：下一步观测分布
* $G_{t+1}$：目标推进反馈分布
* $R_{t+1}$：与后续排序相关的辅助反馈或局部回报

$\Phi_{b,e}$ 的作用是：

* 统一“这个候选能不能解释未来”
* 统一“这个动作是否能区分候选”
* 统一“提升/重写是否保留了任务相关信息”

### 5.4 结构发现算子

保持：

$$
D_b^t : (i_t, X_b^t, K_t) \to \mathcal P_{\mathrm{fin}}(\mathrm{Ob}(\mathcal E_b))
$$

但 v0.5 强调：
其输出的每个新候选 $e$，都应至少近似附带一个粗粒度预测通道 $\widehat{\Phi}_{b,e}$。

因为如果一个结构候选不能改变对未来的预测，它就不值得作为显式候选长期保留。

---

## 6. 惰性机制：从“展开价值”升级为“信息价值”

### 6.1 LazySelect

保留 v0.4：

$$
\mathrm{LazySelect}_t :
(\Sigma_{g,\ell,t}, B_t) \to (L_t^{obj}, L_t^{evt}, L_t^{str})
$$

但对每个候选 $x$ 的价值，v0.5 改写为：

$$
\mathrm{Value}_t(x)
=
\alpha\,\Delta I_{\text{task}}(x)
+ \beta\,\Delta I_{\text{model}}(x)
+ \gamma\,\Delta V_{\text{reuse}}(x)
- \kappa\,\mathrm{ExpandCost}(x)
$$

其中：

* $\Delta I_{\text{task}}(x)$：展开 $x$ 后，任务后验的预期熵下降
* $\Delta I_{\text{model}}(x)$：展开 $x$ 后，对竞争结构或模型的区分增益
* $\Delta V_{\text{reuse}}(x)$：其结果是否可服务多个语境或多个结构候选
* $\mathrm{ExpandCost}(x)$：展开代价

于是：

$$
L_t
=
\operatorname{arg\,max}_{Y,\ \mathrm{cost}(Y) \le B_t}
\sum_{x \in Y} \mathrm{Value}_t(x)
$$

### 6.2 Force

保持 v0.4 的 Force 算子：

$$
\mathrm{Force}_t :
(L_t^{obj}, L_t^{evt}, L_t^{str}, i_t, \{X_b^t\}_b)
\mapsto
(i_t^{+}, \{X_b^{t,+}\}_b)
$$

但 v0.5 明确规定：

> Force 的作用不是“把候选求值出来”，而是“把对未来信息处理最有价值的候选求值出来”。

---

## 7. 联合筛选：从 MDL 到 “MDL + 信息收缩”

### 7.1 基本联合评分

延续 v0.3 / v0.4：

$$
\mathrm{Score}_t(b,e)
=
\mathrm{Fit}_t(b,e)
- \lambda L_{\mathcal B}(b)
- \gamma L_{\mathcal E}(e \mid b)
+ \beta \, \mathrm{VOI}_t(b,e)
$$

或

$$
\mathrm{MDL}_t(b,e)
=
L_{\mathcal B}(b) + L_{\mathcal E}(e \mid b) + L_{\mathrm{res}}(h_t \mid b,e)
$$

### 7.2 v0.5 的统一改写

v0.5 中，把 $\mathrm{VOI}$ 与后验收缩显式化：

$$
\mathrm{Score}_t^{(0.5)}(b,e)
=
\mathrm{Fit}_t(b,e)
- \lambda L_{\mathcal B}(b)
- \gamma L_{\mathcal E}(e \mid b)
+ \beta\,\mathrm{EIG}_t(b,e)
+ \eta\,\mathrm{Shrink}_t(b,e)
$$

其中：

$$
\mathrm{EIG}_t(b,e)
=
\mathbb{E}\left[
D(\mu_{t+1} \,\|\, \mu_t)
\mid b,e
\right]
$$

$\mathrm{Shrink}_t(b,e)$ 表示候选支持集收缩率。

直观上：

* MDL 奖励短解释
* EIG 奖励能带来新信息的候选
* Shrink 奖励能让搜索空间快速塌缩的候选

---

## 8. 结构保持式提升：把“值得提升”改成“近似充分”

### 8.1 提升算子

保持：

$$
A_b : \mathcal E_b^{\mathrm{sel}} \to \mathcal T_b
$$

### 8.2 提升的近似充分性条件

对候选 $e$，若其提升 $A_b(e)$ 满足：

$$
D\!\bigl(
P(O_{t+1}, G_{t+1} \mid i_t, a_t, e)
\,\|\,
P(O_{t+1}, G_{t+1} \mid i_t, a_t, A_b(e))
\bigr)
\le \varepsilon_A
$$

则称 $A_b(e)$ 是对 $e$ 的合法提升。

含义是：

> 把低层结构压成高层任务对象之后，对未来观测与目标推进的预测几乎不变。

这就是 v0.5 对“合法抽象”的正式刻画。

### 8.3 提升优先级

定义：

$$
\mathrm{PromoteScore}_t(e)
=
\alpha\,\Delta \mathrm{Shrink}
+ \beta\,\Delta \mathrm{Reuse}
+ \gamma\,\Delta \mathrm{PlanStability}
- \lambda\,\Delta \mathrm{Loss}_{\Phi}
$$

其中 $\Delta \mathrm{Loss}_{\Phi}$ 表示提升前后预测通道差异。

---

## 9. 语义重写：从“语义测试等价”到“预测通道等价”

### 9.1 重写算子

保持：

$$
N_b : \mathcal E_b \to \overline{\mathcal E}_b
$$

且要求：

$$
Q_b(N_b(e)) = Q_b(e)
$$

### 9.2 v0.5 新增的通道等价条件

除了原有的参考语义测试族 $Q_b$ 外，再要求：

$$
D\!\bigl(
\Phi_{b,e}
\,\|\,
\Phi_{b,N_b(e)}
\bigr)
\le \varepsilon_N
$$

含义是：

> 重写不仅应保持当前语义签名，还应尽量保持对未来观测/行动后果的预测通道不变。

这样，重写就不只是句法归一化，而是：
**信息等价结构的合并。**

---

## 10. 动作选择：显式分离 exploit 价值与 probe 价值

### 10.1 双模态保持不变

$$
a_t=
\begin{cases}
a_t^{\text{probe}} & \text{if uncertainty high} \\
a_t^{\text{exploit}} & \text{if dominant hypothesis stable}
\end{cases}
$$

### 10.2 exploit 动作

$$
a_t^{\text{exploit}}
=
\operatorname{arg\,max}_{a \in \mathcal A(i_t)}
\mathbb{E}\left[
V_{\text{solve}}(a)
- \lambda_{\text{cost}} c(a)
- \lambda_{\text{risk}} r(a)
\right]
$$

### 10.3 probe 动作

$$
a_t^{\text{probe}}
=
\operatorname{arg\,max}_{a \in \mathcal A(i_t)}
\left(
\alpha\,I(B; O_{t+1} \mid i_t, a)
+ \beta\,I(E; O_{t+1} \mid i_t, a)
+ \gamma\,V_{\text{frontier}}(a)
- \lambda_{\text{cost}} c(a)
- \lambda_{\text{risk}} r(a)
\right)
$$

其中：

* $B$：任务语境随机变量
* $E$：结构候选随机变量

也就是说：

* exploit 优先最大化任务推进
* probe 优先最大化信息增益与可证伪性

---

## 11. 主循环：v0.5 最小算法框架

### 11.1 初始化

$$
i_0 = C_K(h_0), \qquad
\mu_0 = \mathrm{InitTaskPosterior}(i_0), \qquad
X_b^0 = \varnothing
$$

若是同一 game 的后续 level，则由 $m_g$ warm-start。

### 11.2 每一步 $t$ 的循环

1. **粗压缩历史**：$i_t \leftarrow C_K^{\text{coarse}}(h_t)$

1. **惰性选择**：$(L_t^{obj}, L_t^{evt}, L_t^{str}) \leftarrow \mathrm{LazySelect}_t(\Sigma_{g,\ell,t}, B_t)$

1. **按需展开**：$(i_t^+, X_t^+) \leftarrow \mathrm{Force}_t(\cdots)$

1. **更新任务后验**：$\mu_t \leftarrow U_{\text{task}}(\mu_{t-1}, i_t^+, a_{t-1}, o_t)$

1. **在高权重任务语境上做结构发现**：$\mathcal C_{b,t+1}^{str} \leftarrow \mathcal C_{b,t}^{str} \cup D_b^t(i_t^+, X_b^t, K_t)$

1. **联合筛选**
   用 $\mathrm{Score}_t^{(0.5)}(b,e)$ 或 MDL + EIG 选 beam 内候选。

1. **结构提升**：$T_b^t = A_b(X_b^{t,\mathrm{sel}})$

1. **语义重写**：$X_b^t \leftarrow N_b(X_b^t)$

1. **选择动作**
   先判定 probe/exploit，再按对应目标函数选动作。

1. **执行动作并更新历史**：$h_{t+1} = h_t \cdot a_t \cdot o_{t+1}$

1. **终止判断**

    若当前 level 到达终局，则退出 level loop。

### 11.3 level 结束后

$$
m_g \leftarrow \mathrm{ConsolidateLevel}(m_g, \{i_t, \mu_t, X_t, \Phi_t\}_t)
$$

### 11.4 game 结束后

$$
K \leftarrow R\bigl(K \sqcup \Delta K_g\bigr)
$$

其中 $\Delta K_g$ 现在不仅包含新结构，也包含：

* 新的高价值 selector / relation schema
* 新的高价值 probe 模式
* 新的通道等价类与重写规则

---

## 12. 失败归因：新增信息流维度

保留 v0.3 的失败类型，并新增两类：

* `BELIEF_FAIL`：历史被压成 $i_t$ 后丢失关键任务信息
* `INFO_VALUE_FAIL`：动作/候选选择没有带来预期的信息增益

因此建议至少保留：

* `PERCEPTION_FAIL`
* `TASK_FAIL`
* `MODEL_FAIL`
* `BELIEF_FAIL`
* `LIFT_FAIL`
* `REWRITE_FAIL`
* `PROBE_FAIL`
* `INFO_VALUE_FAIL`
* `PLAN_FAIL`
* `EXECUTION_FAIL`

其中：

* `BELIEF_FAIL`：压缩后状态对未来观测或决策不再近似充分
* `INFO_VALUE_FAIL`：LazySelect 或 probe 排序没有优先选中真正高信息价值的候选或动作

---

## 13. v0.5 的最小实现原则

为了让 v0.5 仍然能落地，而不是只增数学味道，建议保留以下工程约束：

### 13.1 不要求全局精确概率

$\mu_t$、$w_t$、$\Phi_{b,e}$ 都可以先用：

* 相对分数
* 近似后验
* 局部归一化权重
* 粗粒度预测类别

实现，不要求一开始就做成严格可积模型。

### 13.2 先做“粗预测通道”

$\Phi_{b,e}$ 一开始可以只预测：

* 下一步观测变化类型
* 是否推进目标
* 是否会证伪某类假设
* 是否会打开新 frontier

而不要求预测完整 frame 分布。

### 13.3 LazySelect 先做启发式近似

一开始不必直接精确估计 $I(B; O_{t+1} \mid a)$，可先用：

* 候选分歧度
* 历史上相似 probe 的证伪率
* 预测通道之间的离散差异
* 支持集收缩率

做代理指标。

### 13.4 提升与重写先做“近似充分”

$\varepsilon_A, \varepsilon_N$ 一开始可以较大，只要求：

* 提升/重写后在一组参考 rollout 上行为近似不变
* 且能换来更短描述、更稳排序、更低搜索成本

---

## 14. v0.5 的一句话总结

v0.5 相比 v0.3 / v0.4 的本质新增，不是又加了一层结构，而是把整个系统改写成：

> **一个在交互中，通过惰性展开候选、维护任务与结构后验、选择高信息价值动作、并在近似充分条件下做提升与重写的复合信息处理系统。**

也就是说：

* v0.3 解决了“骨架”
* v0.4 解决了“惰性调度”
* **v0.5 解决的是“信息流、更新、价值与抽象合法性”**

[1]: https://raw.githubusercontent.com/YSystemLabs/struct-agi/arc-agi-3/phase2/docs/%E9%9D%A2%E5%90%91%20ARC-AGI-3%20%E7%9A%84%E5%BD%A2%E5%BC%8F%E5%8C%96%E6%96%B9%E6%A1%88.md "raw.githubusercontent.com"
[2]: https://docs.arcprize.org/games?utm_source=chatgpt.com "Games - ARC-AGI-3 Docs"
