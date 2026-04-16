# 面向 ARC-AGI-3 的形式化方案

> 版本：v0.4
>
> 状态：草案
>
> 定位：在 v0.3 的骨架上，增加惰性调度机制。

## 0. 设计原则

v0.4 保持 v0.3 的主结构不变：

$$
\mathcal H_E \xrightarrow{C_K} \mathcal I \xleftarrow{\Pi} \mathcal B_{\text{task}} \xleftarrow{p} \mathcal E
$$

其中：

* $\mathcal H_E$：交互历史层
* $\mathcal I$：信息状态层
* $\mathcal B_{\text{task}}$：任务语境层
* $\mathcal E$：任务条件化的结构/模型/计划层

本版新增的核心原则只有一句：

> **惰性不是不确定性的本体定义，而是候选对象与候选结构的按需展开机制。**

也就是说：

* 不确定性本身仍由“候选族 + 权重/后验 + 约束未定”来表示；
* 惰性只决定：**哪些候选现在展开，哪些继续悬置**；
* 需要靠动作获取的信息，仍由外部交互解决，而不是靠内部惰性求值解决。

因此，v0.4 的主体仍然是 v0.3；惰性只在信息层、结构层和算法循环中作为“调度与求值机制”加入。

---

## 1. 总结构保持不变

仍采用四层链条：

$$
\mathcal H_E \xrightarrow{C_K} \mathcal I \xleftarrow{\Pi} \mathcal B_{\text{task}} \xleftarrow{p} \mathcal E
$$

并保持以下解释：

* 历史层负责记录真实交互；
* 信息层负责对历史做压缩与抽象；
* 任务层负责维护任务语境后验；
* 结构层负责在任务条件下做结构发现、筛选、提升与重写。

v0.4 的变化只在于：

1. 信息层不再把对象化/事件化写成单值对象，而写成**候选族 + 激活子集 + 缓存**；
2. 结构层候选池不再默认“全部展开”，而加入**惰性结构展开状态**；
3. 算法循环中增加一个显式的 **LazySelect / Force** 步骤。

---

## 2. 历史层 $\mathcal H_E$

与 v0.3 相同。

定义历史：

$$
h_t = (o_0,a_0,o_1,\dots,a_{t-1},o_t)
$$

对象是有限合法历史，态射是一步扩展：

$$
h_t \to h_{t+1}
$$

这一层不引入惰性，因为它只是原始事实记录。

---

## 3. 信息层 $\mathcal I$：加入惰性对象化与惰性事件化

## 3.1 从单值状态改为候选族状态

v0.3 中信息状态写为：

$$
i_t=
(\mathsf{Obj}_t,\mathsf{Evt}_t,\mathsf{Inv}_t,\mathsf{Aff}_t,\mathsf{Mem}_t,\mathsf{Graph}_t)
$$

v0.4 将其改为：

$$
i_t=
(\Omega_t^{obj},\Omega_t^{evt},\mathsf{Inv}_t,\mathsf{Aff}_t,\mathsf{Mem}_t,\mathsf{Graph}_t,\Lambda_t)
$$

其中：

* $\Omega_t^{obj}$：对象化候选池
* $\Omega_t^{evt}$：事件解释候选池
* $\Lambda_t$：惰性调度状态

其余项保持原义：

* $\mathsf{Inv}_t$：不变量/约束
* $\mathsf{Aff}_t$：affordance 候选
* $\mathsf{Mem}_t$：压缩历史索引
* $\mathsf{Graph}_t$：状态—动作探索图

---

## 3.2 对象化候选池

定义：

$$
\Omega_t^{obj}=(\mathcal C_t^{obj},w_t^{obj},A_t^{obj},Z_t^{obj})
$$

其中：

* $\mathcal C_t^{obj}$：对象化候选集合
* $w_t^{obj}$：候选权重/后验/优先级
* $A_t^{obj}\subseteq \mathcal C_t^{obj}$：当前已激活并真正展开的子集
* $Z_t^{obj}$：对象化过程的共享缓存、剪枝约束、部分结果

直观上：

* $\mathcal C_t^{obj}$ 表示“可能怎样看这张图/这段 frame”
* $A_t^{obj}$ 表示“本轮我们真的展开并使用了哪些看法”
* 其余候选仍然保留，但不强制求值

---

## 3.3 事件解释候选池

类似地定义：

$$
\Omega_t^{evt}=(\mathcal C_t^{evt},w_t^{evt},A_t^{evt},Z_t^{evt})
$$

其中：

* $\mathcal C_t^{evt}$：事件解释候选集合
* $w_t^{evt}$：候选权重
* $A_t^{evt}$：已激活并展开的事件候选
* $Z_t^{evt}$：共享缓存与中间结果

---

## 3.4 惰性调度状态

定义：

$$
\Lambda_t=(B_t,\rho_t,\chi_t)
$$

其中：

* $B_t$：当前步内部计算预算
* $\rho_t$：当前调度策略参数
* $\chi_t$：已展开候选的依赖痕迹与缓存命中信息

这里不把 $\Lambda_t$ 做得太重。
它只是说明：系统内部不是“候选一生成就全展开”，而是要受预算与任务相关性约束。

---

## 3.5 信息更新

信息状态仍由压缩映射产生：

$$
i_t = C_K(h_t)
$$

但 $C_K$ 的输出现在不是单一对象图，而是候选族状态。
因此它更准确地说应分为两步：

$$
C_K = C_K^{\text{coarse}} \circ \mathrm{Materialize}
$$

其中：

* $C_K^{\text{coarse}}$：先生成粗候选池与粗摘要
* $\mathrm{Materialize}$：只对部分候选进行按需展开

不过在 v0.4 中，这一步无需作为单独函子强调；只需在实现上承认：**压缩映射本身允许未完全求值。**

---

## 4. 任务层 $\mathcal B_{\text{task}}$

任务层定义保持不变。

任务语境对象：

$$
b=(G_b,P_b,R_b,H_b)
$$

其中：

* $G_b$：目标语义
* $P_b$：进展语义
* $R_b$：相关性准则
* $H_b$：历史视界

任务候选由信息状态诱导：

$$
\Pi(i_t)\subseteq \mathrm{Ob}(\mathcal B_{\text{task}})
$$

维护任务后验：

$$
\mu_t \in \Delta(\Pi(i_t))
$$

v0.4 中惰性不改变任务层本体，只影响：
**任务后验更新之前，到底强制展开了哪些对象化/事件化候选。**

因此任务层仍是“解释层”，惰性只是其下方的求值闸门。

---

## 5. 结构层 $p:\mathcal E\to\mathcal B_{\text{task}}$：加入惰性结构展开

## 5.1 纤维对象保持原义

对每个任务语境 (b)，纤维对象仍定义为：

$$
e=(O_e,Rel_e,Dyn_e,Sch_e;\ g_e,m_e,\pi_e,w_e,\delta_e)
$$

含义不变：

* $O_e$：对象化方式
* $Rel_e$：关系结构
* $Dyn_e$：局部动力学
* $Sch_e$：子目标/策略骨架
* $g_e$：绑定目标解释
* $m_e$：绑定模型
* $\pi_e$：局部计划
* $w_e$：权重
* $\delta_e$：诊断/反例痕迹

---

## 5.2 活跃结构候选池改成惰性候选池

v0.3 中可以把 $X_b^t$ 理解为“当前任务语境 $b$ 下的活跃结构候选池”。

v0.4 将其改成：

$$
X_b^t=(\mathcal C_{b,t}^{str},w_{b,t}^{str},A_{b,t}^{str},Z_{b,t}^{str})
$$

其中：

* $\mathcal C_{b,t}^{str}$：候选结构集合
* $w_{b,t}^{str}$：候选结构权重
* $A_{b,t}^{str}\subseteq \mathcal C_{b,t}^{str}$：当前已激活并真正展开的结构候选
* $Z_{b,t}^{str}$：结构展开共享缓存、可复用中间结果、剪枝约束

这样，结构发现 $D_b^t$ 的输出不再默认全部强制求值，而是：

* 先把候选加入 $\mathcal C_{b,t}^{str}$
* 再由惰性调度器决定哪些候选进入 $A_{b,t}^{str}$

---

## 6. 惰性机制：调度与求值，而非本体

这是 v0.4 新增的核心。

## 6.1 惰性选择器

定义惰性调度器：

$$
\mathrm{LazySelect}_t:
(\Sigma_{g,\ell,t},B_t)\to
(L_t^{obj},L_t^{evt},L_t^{str})
$$

其中：

* $\Sigma_{g,\ell,t}$：当前系统状态
* $B_t$：当前步内部计算预算
* $L_t^{obj}\subseteq \mathcal C_t^{obj}$：本轮要 force 的对象化候选
* $L_t^{evt}\subseteq \mathcal C_t^{evt}$：本轮要 force 的事件候选
* $L_t^{str}\subseteq \bigcup_b \mathcal C_{b,t}^{str}$：本轮要 force 的结构候选

---

## 6.2 惰性选择准则

可定义统一的选择目标：

$$
L_t=
\mathop{\mathrm{arg\,max}}_{Y,\ \mathrm{cost}(Y)\le B_t}
\sum_{x\in Y}
\Big(
\alpha\,\Delta V_{\text{solve}}(x)
+\beta\,\Delta V_{\text{falsify}}(x)
+\gamma\,\Delta V_{\text{reuse}}(x)
-\kappa\,\mathrm{ExpandCost}(x)
\Big)
$$

其中：

* $\Delta V_{\text{solve}}(x)$：展开候选 $x$ 后，对当前求解价值的提升
* $\Delta V_{\text{falsify}}(x)$：展开后对淘汰错误假设的价值
* $\Delta V_{\text{reuse}}(x)$：展开结果是否可复用、能否服务多个任务语境/结构候选
* $\mathrm{ExpandCost}(x)$：展开代价

这一定义明确体现：

> 惰性不是“省算力”这么简单，而是“在给定预算下优先展开最有任务价值、区分价值和复用价值的候选”。

---

## 6.3 Force 算子

定义按需展开算子：

$$
\mathrm{Force}_t:
(L_t^{obj},L_t^{evt},L_t^{str},i_t,{X_b^t}_b) \mapsto (i_t^{+},{X_b^{t,+}}_b)
$$

其中：

* 把选中的对象化候选并入 $A_t^{obj}$
* 把选中的事件候选并入 $A_t^{evt}$
* 把选中的结构候选并入 $A_{b,t}^{str}$
* 同时更新缓存 $Z$ 与依赖痕迹 $\chi_t$

这样：

* 候选可以存在但未展开；
* 只有被 `Force` 的候选才进入当前步的正式推理。

---

## 7. 核心算子保持原义，只在输入上接纳惰性状态

## 7.1 任务后验更新

仍定义：

$$
\mu_{t+1}(b)\propto \mu_t(b)\cdot \mathrm{Lik}(o_{t+1}\mid i_t,a_t,b)
$$

但这里的 $i_t$ 已经是“部分展开后”的信息状态。
所以任务后验更新实际依赖：

* 当前已激活的对象化候选
* 当前已激活的事件解释候选
* 未激活候选通过其粗摘要或先验约束间接影响更新

---

## 7.2 结构发现算子

仍定义：

$$
D_b^t:(i_t,X_b^t,K_t)\to \mathcal P_{\mathrm{fin}}(\mathrm{Ob}(\mathcal E_b))
$$

但它现在产生的是**候选结构集合**，默认先进入 $\mathcal C_{b,t}^{str}$，而不必全部立刻展开。

也就是说：

```math
\mathcal C_{b,t+1}^{str}
=
\mathcal C_{b,t}^{str}\cup D_b^t(i_t,X_b^t,K_t)
```

然后再由惰性机制决定哪些候选进入 $A_{b,t+1}^{str}$。

---

## 7.3 联合筛选算子

仍采用：

```math
\mathrm{Score}_t(b,e)
=
\mathrm{Fit}_t(b,e)
-\lambda L_{\mathcal B}(b)
-\gamma L_{\mathcal E}(e\mid b)
+\beta \mathrm{VOI}_t(b,e)
```

或

```math
\mathrm{MDL}_t(b,e)
=
L_{\mathcal B}(b)+L_{\mathcal E}(e\mid b)+L_{\mathrm{res}}(h_t\mid b,e)
```

但在实现上只对：

* 已展开候选
* 或已有足够摘要可近似评分的候选

进行评分。

因此筛选也具有惰性：
**不是所有候选都要完整评分后再选，而是允许粗评分 → 选择性展开 → 细评分。**

---

## 7.4 结构保持式提升

保持：

$$
A_b:\mathcal E_b^{\mathrm{sel}}\to \mathcal T_b
$$

不变。

惰性只影响：

* 哪些结构候选已经足够展开，可以进入 $\mathcal E_b^{\mathrm{sel}}$
* 哪些结构还停留在“提升种子”状态，不足以进入 $A_b$

所以 $A_b$ 仍然是提升，不是调度。

---

## 7.5 语义重写

保持：

$$
N_b:\mathcal E_b\to \overline{\mathcal E}_b
$$

且要求：

$$
Q_b(N_b(e))=Q_b(e)
$$

不变。

惰性只影响：

* 是否立刻比较两个候选的语义等价
* 是否先缓存部分测试签名，延后做完整重写

所以 $N_b$ 仍然是规范化，不是求值策略。

---

## 8. 动作选择保持 v0.3 双模态，只增加“展开收益”的影响

## 8.1 probe / exploit 双模态保持不变

$$
a_t=
\begin{cases}
a_t^{\text{probe}} & \text{if uncertainty high} \\
a_t^{\text{exploit}} & \text{if dominant hypothesis stable}
\end{cases}
$$

---

## 8.2 动作效用保持不变

$$
a_t=\mathop{\mathrm{arg\,max}}_{a\in\mathcal A(i_t)} J(a\mid i_t,\mu_t,{X_b^t})
$$

其中：

$$
J=
\lambda_{\text{solve}}V_{\text{solve}}
+\lambda_{\text{falsify}}V_{\text{falsify}}
+\lambda_{\text{frontier}}V_{\text{frontier}}
-\lambda_{\text{cost}}c
-\lambda_{\text{risk}}r
$$

---

## 8.3 新增“内部展开收益”只用于内部调度，不直接替代动作效用

这里要特别强调：

* 惰性选择器解决的是**内部该算什么**
* 动作选择器解决的是**外部该做什么**

两者不能混成一个东西。

因此，惰性相关的收益
$$
\Delta V_{\text{solve}},\ \Delta V_{\text{falsify}},\ \Delta V_{\text{reuse}}
$$
只用于内部 `LazySelect`，不直接替代环境动作上的 $J(a)$。

这保证：

> 惰性只是调度与求值机制，不偷换成 agent 的主行为本体。

---

## 9. 系统状态：只做最小改动

v0.3 的核心状态是：

$$
\Sigma_{g,\ell,t}=(K,\ m_g,\ i_{g,\ell,t},\ \mu_{g,\ell,t},\ X_{g,\ell,t})
$$

v0.4 保持形式不变，只把 $i$ 和 $X$ 的内容换成惰性版本：

$$
\Sigma_{g,\ell,t}=
(K,\ m_g,\ i_{g,\ell,t},\ \mu_{g,\ell,t},\ {X_{b,g,\ell,t}}_b)
$$

其中：

* $i_{g,\ell,t}$ 现在包含 $(\Omega^{obj},\Omega^{evt},\Lambda)$
* $X_{b,g,\ell,t}$ 现在是惰性结构候选池 $(\mathcal C,w,A,Z)$

---

## 10. v0.4 最小算法框架

下面只在 v0.3 的主循环中插入一层惰性调度。

### 10.1 初始化

$$
i_0=C_K(h_0),\qquad
\mu_0=\mathrm{InitTaskPosterior}(i_0),\qquad
X_b^0=\varnothing
$$

若是同 game 后续 level，则用 $m_g$ warm-start。

---

### 10.2 主循环

对每一步 $t$：

#### Step 1：粗压缩历史

$$
i_t^{\text{coarse}}=C_K(h_t)
$$

得到粗候选池，但不全部展开。

#### Step 2：更新任务后验

$$
\mu_t=\mathrm{UpdateTaskPosterior}(i_t^{\text{coarse}},\mu_{t-1})
$$

#### Step 3：惰性选择

```math
(L_t^{obj},L_t^{evt},L_t^{str})
=
\mathrm{LazySelect}_t(\Sigma_{g,\ell,t},B_t)
```

#### Step 4：按需展开

```math
(i_t,{X_b^t}_b)
=
\mathrm{Force}_t(L_t^{obj},L_t^{evt},L_t^{str},i_t^{\text{coarse}},{X_b^{t-1}}_b)
```

#### Step 5：高权重任务语境下做结构发现

对所有高权重 $b$：

$$
\mathcal C_{b,t}^{str}
\leftarrow
\mathcal C_{b,t}^{str}\cup D_b^t(i_t,X_b^t,K)
$$

#### Step 6：联合筛选

只对当前可评分候选做 joint score / joint MDL 筛选。

#### Step 7：结构保持式提升

$$
T_b^t=A_b(X_b^{t,\mathrm{sel}})
$$

#### Step 8：语义重写

$$
X_b^t\leftarrow N_b(X_b^t)
$$

#### Step 9：选择动作

根据当前不确定性判定 probe 或 exploit，再用 $J(a)$ 选动作。

#### Step 10：执行动作并更新历史

$$
h_{t+1}=h_t\cdot a_t\cdot o_{t+1}
$$

#### Step 11：终止判断

若当前 level 到达终局，则退出 level loop。

---

### 10.3 level 结束后

更新 game 内记忆：

$$
m_g \leftarrow \mathrm{ConsolidateLevel}(m_g,{i_t,\mu_t,X_t}_t)
$$

---

### 10.4 game 结束后

更新长期知识：

$$
K \leftarrow R\bigl(K\sqcup \Delta K_g\bigr)
$$

---

## 11. 新增两个可检验条件

在 v0.3 原有条件基础上，v0.31 额外要求：

## (L1) 惰性有效性

在大多数步骤中，真实展开量应显著小于候选总量：

$$
|A_t^{obj}| \ll |\mathcal C_t^{obj}|,\qquad
|A_t^{evt}| \ll |\mathcal C_t^{evt}|,\qquad
|A_{b,t}^{str}| \ll |\mathcal C_{b,t}^{str}|
$$

否则惰性只是名义存在。

## (L2) 惰性不破坏任务推进

虽然只展开部分候选，但主导任务后验和有效计划仍应收缩并推进：

$$
H(\mu_t)\downarrow,\qquad
V_{\text{solve}}(\text{selected action}) \uparrow
$$

如果惰性导致大量关键候选长期不被 force，则说明调度策略有问题。

---

## 12. v0.4 的一句话总结

> v0.4 = v0.3 主体 + candidate-family semantics + lazy materialization

更展开一点：

* 信息不确定性：由候选族表示
* 对象化/事件化/结构化：默认不全展开
* 惰性：决定本轮内部该算什么
* 动作：决定本轮外部该试什么
* 提升与重写：仍然是结构层核心，不被惰性替代

---

我觉得这个版本比较接近你想要的平衡：
**主体还是 v0.3，惰性被正式纳入，但只作为调度与求值机制出现，没有抢走框架主位。**
