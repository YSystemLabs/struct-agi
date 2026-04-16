# 面向 ARC-AGI-3 的形式化方案

> 版本：v0.6
>
> 状态：草案
>
> 定位：在 v0.5 的 Markov 范畴信息几何骨架上，加入最小必要的 Information Bottleneck 增补，使形式化不仅说明“信息如何通过交互通道被获取、压缩、更新与复用”，也明确“每一层到底该保什么、丢什么、如何近似优化”。

---

## 0. 设计原则

v0.6 保持 v0.5 的主结构不变：

```math
\mathcal H_E \xrightarrow{C_K} \mathcal I \xleftarrow{\Pi} \mathcal B_{\text{task}} \xleftarrow{p} \mathcal E
```

其中：

* $\mathcal H_E$：交互历史层
* $\mathcal I$：信息状态层
* $\mathcal B_{\text{task}}$：任务语境层
* $\mathcal E$：任务条件化的结构/模型/计划层

v0.6 继续保留 v0.5 的四条原则：

### 0.1 通道原则

ARC-AGI-3 的本体不是静态输入输出映射，而是状态、动作、环境反馈、观测更新、多回合复合所构成的通道系统。

### 0.2 信息收缩原则

系统目标不是简单“解释当前历史”，而是在动作成本与计算预算下，尽快收缩与任务无关的不确定性，并保留对未来决策真正有用的信息。

### 0.3 惰性仅是调度，不是不确定性的本体

不确定性仍由候选族、权重、后验与约束表示；惰性只决定哪些候选现在展开，哪些继续悬置。

### 0.4 合法抽象原则

抽象不是任意压缩；抽象必须尽量不损伤未来观测预测、目标推进、动作排序所需的信息。

---

## 0.5 v0.6 新增原则：分层任务变量原则

v0.5 已经要求“近似充分”，但没有把“对什么充分”显式写出来。
v0.6 明确采用**分层任务变量**：

* $Y_C$：信息状态层的任务变量
* $Y_B$：任务语境层的任务变量
* $Y_E$：结构层的任务变量
* $Y_R$：提升/重写层的任务变量

含义是：

> 不同层压缩的不是同一个全局 $Y$，而是各自那一层真正服务的任务变量。

---

## 0.6 v0.6 新增原则：局部最小充分表示原则

v0.6 不把 IB 当作替代框架，而把它当作局部约束：

```math
\min I(X;T)-\beta I(T;Y)
```

其中：

* $X$：该层输入
* $T$：该层构造出的表示
* $Y$：该层任务变量

含义是：

* 尽量少保留输入中的无关细节
* 尽量保留对本层任务变量真正相关的信息

v0.6 不要求精确求解该目标；它首先是一个**局部设计准则**，其次才是潜在训练目标。([Princeton University][2])

---

## 1. 总结构：四层链条与交互通道

v0.6 仍采用四层链条：

```math
\mathcal H_E \xrightarrow{C_K} \mathcal I \xleftarrow{\Pi} \mathcal B_{\text{task}} \xleftarrow{p} \mathcal E
```

并额外显式引入：

* 环境隐藏状态空间 $S$
* 动作空间 $\mathcal A$
* 观测空间 $\mathcal O$

定义环境通道：

```math
T_{\mathrm{env}} : S_t \otimes A_t \rightsquigarrow O_{t+1}\otimes S_{t+1}
```

于是一步交互写成：

```math
b_t \xrightarrow{\pi_t} a_t \xrightarrow{T_{\mathrm{env}}} o_{t+1} \xrightarrow{U_t} b_{t+1}
```

其中 $b_t$ 为广义内部 belief state，在本方案中由 $(i_t,\mu_t,X_t)$ 联合承担。

---

## 2. 历史层 $\mathcal H_E$：真实交互轨迹

历史定义保持不变：

```math
h_t=(o_0,a_0,o_1,\dots,a_{t-1},o_t)
```

定义范畴 $\mathcal H_E$：

* 对象：所有有限合法历史 $h_t$
* 态射：一步扩展 $h_t\to h_{t+1}$

历史扩展由环境通道诱导：

```math
h_{t+1}=h_t\cdot a_t\cdot o_{t+1},
\qquad
o_{t+1}\sim T_{\mathrm{env}}(s_t,a_t)
```

历史层不做压缩；压缩从 $C_K$ 开始。

---

## 3. 信息状态层 $\mathcal I$：belief construction 与局部瓶颈

### 3.1 总体定义

```math
i_t=
(\Omega_t^{obj},\Omega_t^{evt},\mathsf{Inv}_t,\mathsf{Aff}_t,\mathsf{Mem}_t,\mathsf{Graph}_t,\Lambda_t)
```

其中：

* $\Omega_t^{obj}$：对象化候选池
* $\Omega_t^{evt}$：事件解释候选池
* $\mathsf{Inv}_t$：当前约束/不变量
* $\mathsf{Aff}_t$：当前 affordance 候选
* $\mathsf{Mem}_t$：压缩历史索引
* $\mathsf{Graph}_t$：状态—动作探索图
* $\Lambda_t$：惰性调度状态

### 3.2 belief construction channel

```math
i_t = C_K(h_t),\qquad
C_K : \mathcal H_E \rightsquigarrow \mathcal I
```

$C_K$ 的职责不是重建完整历史，而是构造一个对后续交互近似充分的信息状态。

### 3.3 本层任务变量 $Y_C$

定义：

```math
Y_C := \bigl(\widetilde O_{t+1},\ \widetilde G_{t+1},\ \widetilde A_t^\star\bigr)
```

其中：

* $\widetilde O_{t+1}$：下一步观测的粗粒度摘要
* $\widetilde G_{t+1}$：目标推进的粗粒度摘要
* $\widetilde A_t^\star$：当前动作排序所需的 sufficient statistics

也就是说，信息状态层不追求保住全部未来细节，只追求保住：

* 下一步预测所需信息
* 任务后验更新所需信息
* 当前动作排序所需信息

### 3.4 信息状态层的局部瓶颈准则

定义局部目标：

```math
\mathcal L_C^{IB} = I(h_t;i_t)-\beta_C I(i_t;Y_C)
```

v0.6 不要求你立刻精确估计这两个互信息；
它要求的是：**把“好信息状态”明确理解成“对 $Y_C$ 近似充分且尽量短”的表示。**

### 3.5 近似充分性的 v0.6 改写

将 v0.5 的未来预测充分性，改写成更局部的版本：

```math
I(i_t;Y_C)\ge I(h_t;Y_C)-\varepsilon_C
```

且同时希望 $I(h_t;i_t)$ 尽量小。

这比“保住全部未来信息”更可实施。

---

## 4. 任务语境层 $\mathcal B_{\text{task}}$：任务后验与任务级瓶颈

### 4.1 任务语境对象

```math
b=(G_b,P_b,R_b,H_b)
```

其中：

* $G_b$：候选目标语义
* $P_b$：候选进展语义
* $R_b$：相关性准则
* $H_b$：历史视界/解释尺度

由信息状态诱导：

```math
\Pi(i_t)\subseteq \mathrm{Ob}(\mathcal B_{\text{task}})
```

维护后验：

```math
\mu_t\in\Delta(\Pi(i_t)),\qquad \mu_t(b)=\Pr(b\mid i_t)
```

### 4.2 任务后验更新通道

```math
U_{\text{task}}:(\mu_t,i_t,a_t,o_{t+1})\rightsquigarrow \mu_{t+1}
```

### 4.3 本层任务变量 $Y_B$

定义：

```math
Y_B := \bigl(\widetilde O_{t+1}^{,task},\ \widetilde G_{t+1}^{,task}\bigr)
```

它表示：

* 不同任务解释下最可区分的观测反馈
* 不同任务解释下最可区分的目标推进模式

### 4.4 任务层的局部瓶颈准则

设 $T_B$ 是任务后验的低维表示或任务摘要，则：

```math
\mathcal L_B^{IB}=I(i_t;T_B)-\beta_B I(T_B;Y_B)
```

这表示：
任务层不需要无限扩张其表示；它只需要保住“区分当前任务解释”真正所需的信息。

### 4.5 probe 的第一目标

保持 v0.5：

```math
a_t^{\text{probe-task}}
=
\mathop{\mathrm{arg\,max}}_a
\mathbb E\big[H(\mu_t)-H(\mu_{t+1})\mid i_t,\mu_t,a\big]
```

或

```math
a_t^{\text{probe-task}}
=
\mathop{\mathrm{arg\,max}}_a I(B;O_{t+1}\mid i_t,a)
```

v0.6 的增补理解是：
probe 的任务层目标也可看作最大化对 $Y_B$ 的区分增益。

---

## 5. 结构层 $p:\mathcal E\to\mathcal B_{\text{task}}$：结构候选、预测通道与结构级瓶颈

### 5.1 纤维对象

```math
e=
(O_e,Rel_e,Dyn_e,Sch_e;\ g_e,m_e,\pi_e,w_e,\delta_e)
```

其中：

* $O_e$：对象化方式
* $Rel_e$：关系结构
* $Dyn_e$：局部动力学
* $Sch_e$：子目标/策略骨架
* $g_e$：绑定目标解释
* $m_e$：绑定模型
* $\pi_e$：局部计划
* $w_e$：权重/复杂度/后验
* $\delta_e$：诊断与反例痕迹

### 5.2 惰性结构候选池

```math
X_b^t=(\mathcal C_{b,t}^{str},w_{b,t}^{str},A_{b,t}^{str},Z_{b,t}^{str})
```

### 5.3 预测通道

保持 v0.5：

```math
\Phi_{b,e}:(i_t,a_t)\rightsquigarrow \Delta(O_{t+1},G_{t+1},R_{t+1})
```

其中：

* $O_{t+1}$：下一步观测分布
* $G_{t+1}$：目标推进反馈分布
* $R_{t+1}$：与后续排序相关的辅助反馈

### 5.4 本层任务变量 $Y_E$

定义：

```math
Y_E := \bigl(\widetilde O_{t+1},\ \widetilde G_{t+1},\ \widetilde R_{t+1}\bigr)
```

它表示结构候选真正应该服务的东西：

* 下一步观测粗摘要
* 目标推进粗摘要
* 动作排序相关反馈

### 5.5 结构层的局部瓶颈准则

若 $T_E$ 是从结构候选 $e$ 中抽出的高层摘要，则：

```math
\mathcal L_E^{IB}=I(e;T_E)-\beta_E I(T_E;Y_E)
```

这意味着：

> 一个结构候选之所以值得长期保留，不在于它“解释很多东西”，而在于它能用较小表示保住对 $Y_E$ 的预测能力。

### 5.6 结构发现算子

```math
D_b^t:(i_t,X_b^t,K_t)\to \mathcal P_{\mathrm{fin}}(\mathrm{Ob}(\mathcal E_b))
```

v0.6 新增要求：

> 一个新候选 $e$ 若无法显著改变对 $Y_E$ 的预测，则不应长期保留。

---

## 6. 惰性机制：从信息价值到“每比特相关性价值”

### 6.1 LazySelect

```math
\mathrm{LazySelect}_t:(\Sigma_{g,\ell,t},B_t)\to (L_t^{obj},L_t^{evt},L_t^{str})
```

### 6.2 候选价值

保留 v0.5 的主结构：

```math
\mathrm{Value}_t(x)
=
\alpha \Delta I_{\text{task}}(x)
+\beta \Delta I_{\text{model}}(x)
+\gamma \Delta V_{\text{reuse}}(x)
-\kappa \mathrm{ExpandCost}(x)
```

v0.6 只增加一个解释层面的约束，不强制写入主公式：

> 在同等信息增益下，优先展开那些“用更少表示代价保住更多任务相关信息”的候选。

这一步先作为**排序偏好**，而不是必须的主公式项。

### 6.3 Force

```math
\mathrm{Force}_t:(L_t^{obj},L_t^{evt},L_t^{str},i_t,{X_b^t}_b)\mapsto(i_t^+,{X_b^{t,+}}_b)
```

含义保持不变：
优先求值那些对未来信息处理最有价值的候选。

---

## 7. 联合筛选：保留 v0.5 主评分，只补充局部瓶颈解释

### 7.1 联合评分

保持 v0.5：

```math
\mathrm{Score}_t(b,e)
=
\mathrm{Fit}_t(b,e)
-\lambda L_{\mathcal B}(b)
-\gamma L_{\mathcal E}(e\mid b)
+\beta \mathrm{EIG}_t(b,e)
+\eta \mathrm{Shrink}_t(b,e)
```

### 7.2 v0.6 的解释增补

v0.6 不强行改写主评分公式，而是补充一条解释原则：

> `Fit + EIG + Shrink` 之外，结构候选还应满足：其表示复杂度上升必须换来对 $Y_E$ 的真实保留。

也就是说：

* MDL 约束复杂度
* EIG 奖励信息增益
* Shrink 奖励支持集收缩
* 而 v0.6 进一步要求：这些增益最终应落实到对 $Y_E$ 的相关信息保留上

---

## 8. 结构保持式提升：IB-合法提升

### 8.1 提升算子

```math
A_b:\mathcal E_b^{\mathrm{sel}}\to \mathcal T_b
```

### 8.2 本层任务变量 $Y_A$

定义：

```math
Y_A := \bigl(\widetilde O_{t+1},\ \widetilde G_{t+1},\ \widetilde A_t^\star\bigr)
```

也就是提升后必须保住的核心任务变量：

* 下一步观测摘要
* 目标推进摘要
* 动作排序所需统计量

### 8.3 IB-合法提升

若 $T=A_b(e)$ 满足：

```math
I(T;Y_A)\ge I(e;Y_A)-\varepsilon_A
```

且同时 $T$ 相比 $e$ 更简洁，则称 $A_b(e)$ 为 **IB-合法提升**。

这比直接要求“完整预测通道近似不变”更容易落地。

### 8.4 提升优先级

```math
\mathrm{PromoteScore}_t(e)
=
\alpha \Delta \mathrm{Shrink}
+\beta \Delta \mathrm{Reuse}
+\gamma \Delta \mathrm{PlanStability}
-\lambda \Delta \mathrm{Complexity}
```

v0.6 新增约束：

> 只有当提升后对 $Y_A$ 的信息保留在可接受阈值内时，才允许进入候选晋升序列。

---

## 9. 语义重写：IB-合法重写

### 9.1 重写算子

```math
N_b:\mathcal E_b\to \overline{\mathcal E}_b
```

### 9.2 原有要求

保持：

```math
Q_b(N_b(e))=Q_b(e)
```

必要时仍可检验：

```math
D!\bigl(\Phi_{b,e},|,\Phi_{b,N_b(e)}\bigr)\le \varepsilon_N
```

### 9.3 本层任务变量 $Y_R$

定义：

```math
Y_R := \bigl(\widetilde O_{t+1}^{,rew},\ \widetilde A_t^{\star,rew}\bigr)
```

即：

* 预测通道的关键摘要
* 后续动作排序的关键统计量

### 9.4 IB-合法重写

若：

```math
I(N_b(e);Y_R)\ge I(e;Y_R)-\varepsilon_R
```

则称该重写为 **IB-合法重写**。

这意味着：

> 重写不是“形式更漂亮”就够了，而必须对下游真正依赖的任务变量近似充分。

---

## 10. 动作选择：保留 v0.5，不改主公式

### 10.1 exploit 动作

```math
a_t^{\text{exploit}}
=
\mathop{\mathrm{arg\,max}}_{a\in\mathcal A(i_t)}
\mathbb E\big[
V_{\text{solve}}(a)-\lambda_{\text{cost}}c(a)-\lambda_{\text{risk}}r(a)
\big]
```

### 10.2 probe 动作

```math
a_t^{\text{probe}}
=
\mathop{\mathrm{arg\,max}}_{a\in\mathcal A(i_t)}
\Big(
\alpha I(B;O_{t+1}\mid i_t,a)
+\beta I(E;O_{t+1}\mid i_t,a)
+\gamma V_{\text{frontier}}(a)
-\lambda_{\text{cost}}c(a)
-\lambda_{\text{risk}}r(a)
\Big)
```

v0.6 不改主公式，只补一条解释：

> probe 的价值不只是带来观测差异，而是带来对 $Y_B$、$Y_E$ 有判别力的观测差异。

---

## 11. 主循环：v0.6 最小算法框架

### 11.1 初始化

```math
i_0=C_K(h_0),\qquad
\mu_0=\mathrm{InitTaskPosterior}(i_0),\qquad
X_b^0=\varnothing
```

### 11.2 每一步 $t$

1. **历史压缩**
   ```math
   i_t\leftarrow C_K(h_t)
   ```
   目标：对 $Y_C$ 近似充分且尽量短

2. **惰性选择**
   ```math
   (L_t^{obj},L_t^{evt},L_t^{str})
   \leftarrow \mathrm{LazySelect}_t(\Sigma_{g,\ell,t},B_t)
   ```

3. **按需展开**
   ```math
   (i_t^+,X_t^+)\leftarrow \mathrm{Force}_t(\cdots)
   ```

4. **更新任务后验**
   ```math
   \mu_t\leftarrow U_{\text{task}}(\mu_{t-1},i_t^+,a_{t-1},o_t)
   ```

5. **结构发现**
   ```math
   \mathcal C_{b,t+1}^{str}
   \leftarrow
   \mathcal C_{b,t}^{str}\cup D_b^t(i_t^+,X_b^t,K_t)
   ```

6. **联合筛选**
   依据 $\mathrm{Score}_t(b,e)$ 选 beam 内候选，并检查其对 $Y_E$ 的信息保留

7. **结构提升**
   ```math
   T_b^t=A_b(X_b^{t,\mathrm{sel}})
   ```
   检查是否为 IB-合法提升

8. **语义重写**
   ```math
   X_b^t\leftarrow N_b(X_b^t)
   ```
   检查是否为 IB-合法重写

9. **动作选择**
   probe / exploit 切换

10. **执行动作并更新历史**
    ```math
    h_{t+1}=h_t\cdot a_t\cdot o_{t+1}
    ```

---

## 12. 失败归因：新增瓶颈失效视角

在 v0.5 的基础上，新增两类推荐归因：

* `BOTTLENECK_FAIL_C`：信息状态 $i_t$ 对 $Y_C$ 不再近似充分
* `BOTTLENECK_FAIL_E`：提升/重写后表示对 $Y_A$ 或 $Y_R$ 丢失关键相关信息

这样可把失败区分为：

* 候选不够
* 更新不够
* 还是“压缩压坏了”

---

## 13. 最小实现原则

### 13.1 不要求精确互信息

实践中不要求直接精确计算 $I(X;T)$、$I(T;Y)$。
可采用：

* predictor-head accuracy
* rollout consistency
* 支持集收缩率
* 任务后验熵下降
* action ranking stability

作为代理。

### 13.2 先定义分层 $Y$，再谈 IB

v0.6 的关键不是“把每层都训练成标准 IB”，而是先明确：

* 这一层到底服务什么任务变量
* 这一层的压缩是否合法

### 13.3 IB 是增补层，不替代 v0.5

v0.6 不推翻 v0.5 的主哲学。
它只把“这一层到底该保什么、丢什么”正式写清楚。

---

## 14. v0.6 的一句话总结

v0.6 相比 v0.5 的本质新增，不是再加一个总框架，而是：

> **把 v0.5 中“近似充分”的要求局部化：每一层都显式绑定自己的任务变量，并把该层表示理解为对该任务变量的最小充分表示。**

也就是说：

* v0.5 解决“全局信息处理骨架”
* **v0.6 进一步解决“这一层具体该保什么、丢什么、如何判断压缩是否合法”**

[1]: https://raw.githubusercontent.com/YSystemLabs/struct-agi/arc-agi-3/phase2/docs/%E9%9D%A2%E5%90%91%20ARC-AGI-3%20%E7%9A%84%E5%BD%A2%E5%BC%8F%E5%8C%96%E6%96%B9%E6%A1%88-0v5.md "raw.githubusercontent.com"
[2]: https://www.princeton.edu/~wbialek/our_papers/tishby%2Bal_99.pdf?utm_source=chatgpt.com "The information bottleneck method"
