# SoftHebb / SoftWTA 关系原型分层最小验证方案

> 版本：v0.2
> 状态：ARC-AGI-2 静态分层最小验证方案草案
> 目标：把“论文忠实复现型验证”和“工程启发型 ARC 前端探索”拆开：先评估 SoftHebb 论文机制能否在无多预序偏置、input-only 的 ARC 关系场上形成稳定 proto-structure；再评估 SoftWTA / SoftHebb 风格原型学习与 multi-preorder 结合后，是否能补强固定模板求解。

---

## 1. 实验动机

原有多预序对象发现实验验证的是：

> 在固定小型模板池和固定搜索闭集下，多预序对象发现是否比常见分割/聚类基线更稳定地产生可复用对象候选，并改善任务内留一训练对预测表现。

v0.1 草案把两个问题混在了一起：

1. SoftHebb 论文里的核心机制，能否迁移到 ARC 的局部关系场前端。
1. SoftWTA / SoftHebb 风格的原型学习，能否作为工程层补强 multi-preorder 与 fixed-template search。

这两个问题不能共用同一个主协议。否则结果会混掉：

* 如果主输入默认带 `multi_preorder_rank_vector`，就不能把结果解释成“自动结构发现”；
* 如果更新规则只是 soft assignment + prototype averaging + diversity penalty，就不能把结果解释成 SoftHebb 本身；
* 如果 prototype 用 train outputs 一起学，就更像任务内共结构学习，而不是 input 端前语义发现。

因此本版文档把实验拆成两层：

* 实验 A：`softhebb_faithful_proto` paper-faithful sanity check。
* 实验 B：SoftWTA / SoftHebb-inspired ARC 前端工程验证，以及与 `multi_preorder_v0_baseline` 的 hybrid 比较。

SoftHebb 论文的相关启发是：它提出 multilayer SoftHebb，一种不依赖 feedback、target 或 error signal 的深层学习算法，并强调 soft winner-take-all、Hebbian、unsupervised、online 等机制。论文在 OpenReview 页面中也明确将其定位为通过 Hebbian plasticity 和 soft winner-take-all 网络推进无反馈深度学习。([OpenReview][2])

---

## 2. 最小命题

本方案只检验三个弱命题，但按层次分别回答。

### 命题 A：paper-faithful SoftHebb 是否优于简单原型基线

在 `input_only + no_preorder` 条件下，`softhebb_faithful_proto` 是否比 `raw_feature_kmeans`、`hard_wta_relation_proto`、`softwta_positive_only` 更稳定地产生 proto-object / proto-relation 候选？

### 命题 B：这些候选是否对固定模板求解有下游价值

在不扩展 DSL、不增加下游模板表达力的前提下，`softhebb_faithful_proto` 或 `softwta_positive_only` 接入 fixed-template search 后，是否相对 `raw_feature_kmeans / hard_wta` 带来 exact / pixel / beam shrink 的改善？

### 命题 C：hybrid 版本是否能补强多预序

把 `multi_preorder_rank_vector` 作为混合输入时，原型学习是否能补强 `multi_preorder_v0_baseline`，并形成更强的候选生成层？

如果只有命题 C 成立，则结论必须写成：

> SoftHebb / SoftWTA 风格机制作为工程补充层有价值，但不足以单独支持“SoftHebb 论文方法已迁移到 ARC 前端结构发现”这一更强结论。

---

## 3. 本实验不验证什么

本实验不验证：

* 开放式变换类自动发明；
* 多对象协同构造；
* 任意程序合成；
* ARC-AGI-3 动态任务信念；
* 主动探测动作选择；
* 跨 level 机制记忆；
* 长期知识自动形成；
* “原型就是语义”。

本方案验证的是两个层次：

> 1. SoftHebb 论文机制能否在 `input_only + no_preorder` 的 ARC 关系场上形成稳定前语义候选；
> 2. 这些候选在 fixed-template search 下是否有工程价值，以及是否能与 multi-preorder 互补。

---

## 4. 总体管线

原有多预序实验管线是：

```text
Grid
→ Local Features / Multi-preorder Field
→ Proto-Objects
→ Object Graph
→ Fixed Template Search
→ Leave-one-out Evaluation
```

本版改为分层管线。

实验 A：paper-faithful sanity check

```text
Grid
→ Minimal Local Relation Field (no preorder)
→ Prototype Learner
  (raw_kmeans / hard_wta / softwta_positive_only / softhebb_faithful)
→ Prototype Activation / Assignment Maps
→ Proto-Object Candidates
→ Representation Diagnostics
→ Optional Fixed Template Search
```

实验 B：engineering / hybrid validation

```text
Grid
→ Relation Field (without_preorder or with_preorder)
→ Prototype Learner
→ Proto-Object Candidates
→ Object Graph
→ Fixed Template Search
→ Leave-one-out Evaluation
```

核心变化只发生在：

```text
Local Relation Field → Proto-Object Candidates
```

但只有实验 A 可以支持“SoftHebb 论文机制是否迁移到 ARC 前端”的判断；实验 B 只支持工程启发或 hybrid 增益的判断。下游模板池、评分函数、留一协议、扰动协议尽量继承原实验设计。原文中固定模板池包括 `identity / translate / recolor / delete / crop_selected_bbox`，候选程序采用 `select(S); T; R` 骨架，且重点是比较不同对象表示在同一模板池、同一选择器集、同一搜索预算下的稳定解释能力。([GitHub][1])

---

## 5. 输入与任务集合

### 5.1 任务来源

优先沿用原多预序实验的任务集合。

纳入条件保持不变：

* 来自 ARC-AGI-2 / ARC training split；
* 每个任务至少 3 个 train pairs；
* 能被固定一元模板池表达；
* 不包含明显输出扩张、重复平铺、多对象协同构造；
* 不临时加入新 DSL primitive。

原多预序实验附表中已经列出了若干适合单对象平移、重着色、裁剪等固定模板验证的任务，例如 `05f2a901`、`25ff71a9`、`dc433765`、`63613498`、`1cf80156` 等。([GitHub][1])

### 5.2 主任务集

建议定义：

```text
S_min_softwta = S_min_multi_preorder
```

也就是先不新增任务，保证和多预序实验可比。

### 5.3 扩展任务集

如果主实验出现正信号，再扩展：

```text
S_ext_softwta =
single_object_translate
+ single_object_recolor
+ crop_selected_bbox
+ simple_delete
+ boundary_touching_object
```

扩展集必须在实验前冻结。

---

## 6. 局部关系场

SoftWTA 不直接吃 raw pixel。

原因是 raw color id 很容易导致伪结构。输入应是局部关系特征，即前语义关系场。

对每个格子或 patch 中心 $u$，构造：

$$
z_u \in \mathbb R^d
$$

其中 $z_u$ 来自以下特征。

### 6.1 最小特征族

建议最小特征包括：

```text
color_role_onehot
same_color_8mask
background_8mask
foreground_flag
boundary_distance_bucket
horizontal_run_length_bucket
vertical_run_length_bucket
local_transition_count
neighbor_color_role_histogram
```

其中：

* `color_role_onehot` 不使用原始颜色编号，而使用颜色角色；
* `same_color_8mask` 表示八邻域同色关系；
* `background_8mask` 表示邻域是否背景；
* `boundary_distance_bucket` 表示到边界的离散距离等级；
* `run_length_bucket` 表示方向连续性；
* `transition_count` 表示局部变化复杂度。

主协议默认不包含 `multi_preorder_rank_vector`。只要这个特征被加入，该配置就必须被标注为 `relation_field_with_preorder` 的 hybrid 模式，而不是 paper-faithful automatic structure discovery。

### 6.2 patch 半径

最小支持：

```text
r ∈ {1, 2}
```

也就是 $3\times3$ 与 $5\times5$ 两种局部视野。

主实验先用：

```text
r = 1
```

扩展实验再加：

```text
r = 2
```

### 6.3 颜色重命名约束

特征必须满足：

> 同步颜色重命名后，除颜色角色重索引外，结构签名应保持不变。

因此禁止直接把颜色 id 当连续数值输入。

### 6.4 hybrid 扩展特征

在实验 B 或专门消融中，可以加入：

```text
multi_preorder_rank_vector
```

这个模式的用途是回答：

> 手工结构偏置与原型学习是否互补。

它不能用于回答：

> SoftHebb 是否在无多预序偏置条件下自动发现了 ARC 结构。

---

## 7. 原型学习器

### 7.1 原型集合

定义 $K$ 个原型：

$$
P = \{p_1,\dots,p_K\}, \quad p_k \in \mathbb R^d
$$

其中 $d$ 是局部关系特征维度。

建议主实验：

```text
K ∈ {8, 16, 32}
```

默认：

```text
K = 16
```

### 7.2 competition scores

对每个局部关系向量 $z_u$，计算：

$$
s_k(u) = \mathrm{sim}(z_u, p_k)
$$

$$
r_k(u) = \exp(s_k(u)/\tau) \big/ \sum_{\ell=1}^{K} \exp(s_\ell(u)/\tau)
$$

其中：

* $r_k(u)$ 是 prototype $k$ 对位置 $u$ 的 soft responsibility；
* $\tau$ 是温度；
* $\mathrm{sim}$ 可以先用 cosine similarity 或 negative squared distance。

Stage 0 主协议默认：

```text
τ = 0.1
```

小范围鲁棒性阶段再扩展到：

```text
τ ∈ {0.1, 0.2}
```

### 7.3 softwta_positive_only

这是工程启发型基线，不是 paper-faithful SoftHebb。

它使用 dense soft assignment 的正向聚合：

$$
p_k \leftarrow \mathrm{normalize}\left( p_k + \eta \sum_u r_k(u)(z_u - p_k) \right)
$$

直观含义：

> 经常共同激活的局部关系模式，会被聚合成稳定原型。

它适合作为 `softwta_positive_only` 的 inspired baseline，但不能被写成 SoftHebb replication。

### 7.4 softhebb_faithful_proto

paper-faithful 变体必须同时包含四个要点：

1. soft WTA competition；
1. winner-only positive Hebbian update；
1. non-winner 的 soft anti-Hebbian update；
1. weight-norm-dependent adaptive learning rate。

定义 winner：

$$
k^\star(u) = \arg\max_k r_k(u)
$$

对 winner 做正向 Hebbian 更新：

$$
p_{k^\star} \leftarrow \mathrm{normalize}\left( p_{k^\star} + \eta_{k^\star}(u)(z_u - p_{k^\star}) \right)
$$

对 non-winner 做 soft anti-Hebbian 更新：

$$
p_k \leftarrow \mathrm{normalize}\left( p_k - \eta_k(u)\, \gamma\, r_k(u)(z_u - p_k) \right), \quad k \ne k^\star(u)
$$

其中 $\eta_k(u)$ 不是常数，而应实现论文强调的自适应学习率机制；如果暂时没有实现 adaptive learning rate，则该方法名必须降级为：

```text
softhebb_like_proto
```

而不是 `softhebb_faithful_proto`。

### 7.5 冗余惩罚与诊断

redundancy penalty 可以作为诊断项或辅评分：

$$
L_{\mathrm{div}} = \sum_{i \lt j} \mathrm{sim}(p_i, p_j)^2 \cdot \mathrm{overlap}(r_i, r_j)
$$

但它不能替代 `softhebb_faithful_proto` 里的 non-winner anti-Hebbian plasticity。

### 7.6 冻结策略与输入模式

每个 LOO fold 中，区分三种模式：

```text
Mode I: input_only
Mode IO: input_output_unpaired
Mode PAIR: paired_delta
```

主协议固定为：

```text
Mode I = input_only
```

具体要求：

1. 只使用拟合集的 $n-1$ 个 train pairs；
1. 只使用这些 pairs 的 input grids 学习 prototype；
1. 冻结 prototype bank；
1. 对留出的 $X_j$ 只做 inference，不用 $Y_j$ 学习 prototype。

`Mode IO` 允许用拟合集的 train inputs + train outputs 共同学习 prototype，但只能作为 task-conditioned 共结构学习 ablation；`Mode PAIR` 显式利用 input-output 差分学习 transition / morphism motif，不属于第一阶段主实验。

无论哪种模式，都禁止使用留出输出 $Y_j$。

---

## 8. 从 prototype activation 到 proto-object

SoftWTA 输出的是 activation map，不是对象。

需要定义一个固定的 objectization 过程。

### 8.1 activation map

对每个 prototype $k$，得到：

$$
A_k(u)=r_k(u)
$$

### 8.2 threshold

对每个 activation map，取候选 mask：

$$
M_{k,\theta}={u\mid A_k(u)\ge \theta}
$$

阈值来自固定小网格：

```text
θ ∈ {0.35, 0.5, 0.65, 0.8}
```

也可加 top-quantile：

```text
top_q ∈ {10%, 20%, 30%}
```

但主实验先用固定阈值。

### 8.3 connected components

对每个 mask 做 cc4 或 cc8：

```text
cc_mode ∈ {cc4, cc8}
```

每个连通分量成为一个 proto-object candidate。

### 8.4 object attributes

每个 proto-object 记录：

```text
support mask
bbox
area
centroid
color role histogram
dominant prototype id
prototype activation mean
prototype activation entropy
boundary contact
shape signature
local relation summary
```

### 8.5 pruning

固定剪枝规则：

```text
min_area ∈ {1, 2}
max_objects_per_grid = 32
min_activation_mean = 0.35
```

如果候选超过 `max_objects_per_grid`，按：

```text
activation_mean × area_normalized × compactness
```

排序保留前 32 个。

---

## 9. 对照组与方法分层

本版把比较对象拆成三组。

### 9.1 表示学习层基线

```text
R_repr = {
  raw_feature_kmeans,
  hard_wta_relation_proto,
  softwta_positive_only,
  softhebb_faithful_proto
}
```

其中：

* `raw_feature_kmeans`：隔离“局部关系特征本身”的贡献；
* `hard_wta_relation_proto`：检验 hard assignment 与 soft competition 的差异；
* `softwta_positive_only`：工程启发型正向聚合基线；
* `softhebb_faithful_proto`：唯一可以支持 SoftHebb paper transfer 结论的主方法。

### 9.2 下游系统层基线

```text
R_sys = {
  cc4,
  cc8,
  bbox,
  multi_preorder_v0_baseline
}
```

其中 `cc4 / cc8 / bbox` 是传统对象化基线，`multi_preorder_v0_baseline` 是强结构偏置基线。

### 9.3 hybrid 方法

```text
R_hybrid = {
  softhebb_with_preorder,
  softwta_positive_with_preorder
}
```

这组方法只回答：

> 手工结构偏置与原型学习是否互补。

它们不能被用于支持“SoftHebb 在无多预序偏置条件下自动发现 ARC 结构”的结论。

---

## 10. 固定下游模板池

下游模板池继承原实验，不允许因 SoftWTA / SoftHebb 新增 primitive。实验 A 可以把 fixed-template search 作为 secondary downstream check；实验 B 则把它作为主评测层。记最小模板池为 $\mathcal A_{\min}$，其五个固定一元原语为：`identity`、`translate`、`recolor`、`delete`、`crop_selected_bbox`。

候选程序统一写成：

$$
\pi = \mathrm{select}(S);\ T;\ R
$$

其中：

* $\mathrm{select}(S)$：固定选择器白名单；
* $T\in\mathcal A_{\min}$：固定一元模板变换；
* $R$：固定渲染方式。

### 10.1 selector 白名单

建议保持小集合：

```text
largest_object
smallest_object
center_object
boundary_touching_object
unique_color_role_object
highest_activation_object
lowest_activation_entropy_object
unique_prototype_role_object
relation_unique_object
```

其中新增的 SoftWTA selector 只有三个：

```text
highest_activation_object
lowest_activation_entropy_object
unique_prototype_role_object
```

注意：这些 selector 也要对所有 prototype 方法开放，不能只给 SoftWTA。

### 10.2 render 白名单

```text
render_all
render_selected
crop_selected_bbox
```

---

## 11. 训练评分

单个候选解释：

$$
e=(r,h,P,\pi)
$$

其中：

* $r$：表示方法；
* $h$：感知假设；
* $P$：prototype bank，如果方法不使用 prototype，则为空；
* $\pi$：候选程序。

注意：$J_{\mathrm{train}}$ 只在方法已经接入 fixed-template search 后才是核心评分。对于实验 A 的 representation sanity check，它不是主判据，只能作为 secondary downstream 指标。

训练评分：

$$
J_{\mathrm{train}}(e) = L_{\mathrm{res}}(e) + \lambda_1 L_{\mathrm{prog}}(e) + \lambda_2 L_{\mathrm{hyp}}(e) + \lambda_3 L_{\mathrm{proto}}(e) + \lambda_4 L_{\mathrm{redun}}(e)
$$

其中：

### 11.1 residual loss

$L_{\mathrm{res}}$：对拟合集 $n-1$ 个 train pairs 的输出残差。

### 11.2 program complexity

$L_{\mathrm{prog}}$：程序长度、模板类型复杂度、参数复杂度。

### 11.3 hypothesis complexity

$L_{\mathrm{hyp}}$：感知假设复杂度，包括：

```text
patch radius
threshold choice
cc mode
color role normalization mode
```

### 11.4 prototype complexity

$L_{\mathrm{proto}} = \log K + N_{\mathrm{act}} + \ell_\tau$，其中 $N_{\mathrm{act}}$ 是活跃 prototype 数（`active_prototypes`）， $\ell_\tau$ 是温度参数离散化后的码长（`quantized_temperature_code_length`）。

### 11.5 redundancy penalty

$$
L_{\mathrm{redun}} = \frac{1}{K(K-1)} \sum_{i \ne j} \mathrm{sim}(p_i, p_j)^2 \cdot \mathrm{overlap}(r_i, r_j)
$$

这个项只用于诊断或辅评分。主结果应同时报告有无该项。

---

## 12. 任务内留一协议

对每个任务：

$$
\{(X_1, Y_1), \dots, (X_n, Y_n)\}
$$

每次留出一个 pair：

$$
(X_j, Y_j)
$$

拟合集为：

$$
D_{-j} = \{(X_i, Y_i) \mid i \ne j\}
$$

### 12.1 实验 A：paper-faithful sanity check

对每个方法 $r\in R_{\mathrm{repr}}$：

1. 在 $D_{-j}$ 的 train inputs 上学习对象表示；
1. 在 $D_{-j}$ 与 $X_j$ 上推断 prototype assignment / activation；
1. 生成 proto-object candidates；
1. 记录 representation metrics、perturbation metrics 与 oracle-style candidate coverage；
1. 可选地把这些 candidates 接到 fixed-template search，作为 secondary downstream check。

### 12.2 实验 B：engineering / hybrid validation

对每个方法 $r\in R_{\mathrm{repr}} \cup R_{\mathrm{hybrid}}$：

1. 在 $D_{-j}$ 上学习或枚举对象表示；
1. 在 $D_{-j}$ 上枚举候选程序；
1. 按 $J_{\mathrm{train}}$ 排序；
1. 保留前 $K_{\mathrm{beam}}$ 个候选；
1. 使用 top-1 候选在 $X_j$ 上预测；
1. 与 $Y_j$ 比较。

主协议默认：

```text
input_mode = input_only
relation_field = without_preorder
```

`input_output_unpaired` 只能作为 ablation；`paired_delta` 不属于第一阶段。

默认：

```text
K_beam = 8
```

扩展：

```text
K_beam ∈ {8, 16}
```

原实验也采用任务内留一训练对验证：用其余 $n-1$ 个 train pairs 拟合程序，再预测留出的训练对输出，并记录 exact match、pixel accuracy 和训练评分。([GitHub][1])

---

## 13. 扰动稳定性协议

继承原多预序实验的两类扰动：

```text
同步颜色重命名
同步平移 / padding
```

原设计中也明确使用同步颜色重命名、同步平移或边界填充扰动，并通过候选解释的规范签名判断操作性等价。([GitHub][1])

### 13.1 prototype 规范签名

对候选解释定义：

$$
\sigma(e) = (\mathrm{tmpl}(\pi),\ \mathrm{sel}(\pi),\ \mathrm{render}(\pi),\ \widetilde{\theta}(\pi),\ \widetilde{h},\ \widetilde{P})
$$

其中 $\widetilde{P}$ 是 prototype bank 的规范摘要。

$\widetilde{P}$ 不保存原始颜色 id 或绝对坐标，只保存：

```text
prototype activation rank
prototype role histogram
relative boundary profile
color-role invariant signature
activation entropy bucket
object count bucket
```

### 13.2 EqK

对扰动前后的 top-K 候选集：

$$
E_K(T,j,r)
$$

定义：

$$
\mathrm{Eq}_K = \big|\,\{\sigma(e)\mid e\in E_K\} \cap \{\sigma(e')\mid e'\in E'_K\}\,\big| \big/ K
$$

主报告：

```text
top1_signature_stable_rate
EqK_mean
EqK_median
```

---

## 14. 主指标

### 14.1 第一层：表示学习主指标

实验 A 的主比较不先看 exact / pixel，而先看表示层是否真的学到更稳定的候选结构。

主指标：

```text
prototype_utilization
prototype_redundancy
seed_stability
perturbation_stability
proto_object_coverage
oracle_topK_candidate
oracle_object_coverage
```

#### prototype utilization

$$
U = \exp\left( -\sum_k \bar r_k \log \bar r_k \right)
$$

表示有效使用了多少 prototype。

#### prototype redundancy

$$
D_{\mathrm{redun}} = \frac{1}{K(K-1)} \sum_{i \ne j} \mathrm{sim}(p_i, p_j)^2 \cdot \mathrm{overlap}(r_i, r_j)
$$

#### seed stability

不同随机种子训练出的 prototype，经匹配后比较：

```text
matched_prototype_similarity
downstream_exact_variance
downstream_pixel_variance
```

#### ablation contribution

对 top-k prototype 逐个移除，记录：

```text
Δ exact
Δ pixel_acc
Δ J_train
Δ beam_size
```

如果一个 prototype 被频繁激活但移除后下游无变化，它可能是伪结构或冗余结构。

### 14.2 第二层：下游工程指标

在实验 A 的 optional downstream check 和实验 B 的主协议中，记录：

```text
top-1 exact match count
mean pixel accuracy
J_train_mean
residual_DL
candidate_object_count
beam_shrink
EqK_mean
top1_signature_stable_rate
no_regression_count
```

### 14.3 第三层：强基线比较

只有当前两层出现正信号后，才挑战：

```text
multi_preorder_v0_baseline
```

这里必须分开写两个结论：

```text
softhebb_faithful_without_preorder vs multi_preorder_v0_baseline
softhebb_with_preorder vs multi_preorder_v0_baseline
```

前者回答“自动发现能否接近强人工偏置”，后者回答“hybrid 是否能补强强人工偏置”。

---

## 15. 通过标准

定义表示学习层基线：

```text
B_repr = {
  raw_feature_kmeans,
  hard_wta_relation_proto,
  softwta_positive_only
}
```

系统层基线：

```text
B_sys = {
  cc4,
  cc8,
  bbox
}
```

强基线：

```text
B_strong = {
  multi_preorder_v0_baseline
}

M_faithful = softhebb_faithful_proto
```

### 15.1 最小通过

满足以下条件，可认为 paper-faithful SoftHebb 迁移通过最小验证：

1. 在 `input_only + no_preorder` 条件下，`M_faithful` 相对 `raw_feature_kmeans` 与 `hard_wta_relation_proto`，至少在下列四项中的三项稳定更优：

```text
prototype_redundancy
prototype_utilization
perturbation_stability
oracle_topK_candidate / oracle_object_coverage
```

1. 相比 `softwta_positive_only`，faithful 版本没有退化成“更复杂但更不稳定”的实现，即：

```text
seed_stability 不更差
representation 指标整体不更差
```

1. 接入 optional downstream fixed-template search 后，mean pixel accuracy 非负增益，且候选数量不爆炸：

```text
candidate_object_count_M <= 1.25 × mean(candidate_object_count_{raw,hard})
```

### 15.2 工程通过

满足最小通过，并且在 fixed-template search 下相对 `raw_feature_kmeans / hard_wta_relation_proto` 至少满足一项：

```text
top-1 exact match 提升
mean pixel accuracy 提升
beam_shrink 改善且 candidate_count 未爆炸
```

### 15.3 强通过

满足工程通过，并且以下二者至少成立其一：

```text
softhebb_faithful_without_preorder 接近或超过 multi_preorder_v0_baseline
softhebb_with_preorder 显著超过 multi_preorder_v0_baseline
```

这两个结论必须单独报告，不能合并成一个“超过 multi_preorder”的模糊说法。

### 15.4 部分通过

如果出现以下任一情况，则只能判为部分通过：

```text
softhebb_faithful_without_preorder > raw/hard，但 < multi_preorder
softhebb_with_preorder > multi_preorder，但 faithful_without_preorder 没有正信号
softwta_positive_only 有正信号，但 softhebb_faithful 没有
```

结论应写成：

> 该机制在 ARC 前端中有工程价值，但还不能单独支持 SoftHebb 论文方法已迁移成功；更合理的表述是补充层或 hybrid 候选生成层。

### 15.5 不通过

如果它只提高训练拟合，但：

```text
留一 exact 不升
pixel accuracy 不升
EqK 下降
candidate count 暴涨
seed variance 很大
```

则认为该原型学习器没有形成稳定结构，只是在增加搜索噪声。

---

## 16. 消融实验

### 16.1 raw pixel vs relation field

比较：

```text
SoftWTA(raw_color_patch)
SoftWTA(relation_field_patch)
```

目的：

> 验证关系场是否必要。

预期：raw pixel 更容易过拟合颜色编号，扰动稳定性更差。

### 16.2 hard vs soft-positive-only

比较：

```text
hard_wta_relation_proto
softwta_positive_only
```

目的：

> 验证 soft competition + dense positive averaging 是否优于 hard assignment。

### 16.3 positive-only vs paper-faithful

比较：

```text
softwta_positive_only
softhebb_faithful_proto
```

目的：

> 验证 winner-only positive、non-winner anti-Hebbian、adaptive learning rate 是否带来真实稳定性收益。

### 16.4 input_only vs input_output_unpaired

比较：

```text
input_only
input_output_unpaired
```

目的：

> 区分“输入端前语义结构发现”和“任务内共结构学习”。

### 16.5 是否使用多预序特征

比较：

```text
relation_field_without_preorder
relation_field_with_preorder_rank_vector
```

目的：

> 判断原型学习是独立自动发现结构，还是只是在强结构偏置上做 hybrid 补强。

### 16.6 prototype 数量

比较：

```text
K = 8, 16, 32
```

目的：

> 检查结构发现是否依赖过大 prototype bank。

### 16.7 温度与自适应学习率

比较：

```text
τ = 0.1, 0.2
adaptive_lr = on / off
```

目的：

> 检查 faithful 版本是否真的依赖论文所强调的关键机制，而不是靠宽松超参数偶然工作。

---

## 17. 实现闭集

建议新增目录：

```text
phase1/scripts/relation_proto_validation/
```

文件结构：

```text
relation_proto_validation/
  README.md
  config.py
  relation_field.py
  prototype_bank.py
  objectize.py
  baselines.py
  fixed_template_search.py
  perturbation.py
  metrics.py
  run_validation.py
  configs/
    relation_proto_v0.yaml
  results/
    .gitkeep
```

### 17.1 relation_field.py

负责：

```text
grid_to_relation_features(grid, config) -> Z
```

输出：

```text
Z: H × W × d
metadata: color roles, background candidate, normalization info
```

### 17.2 prototype_bank.py

负责：

```text
fit_prototype_bank(Z_list, config) -> PrototypeBank
infer_responsibility(Z, bank) -> R
```

支持：

```text
method = raw_feature_kmeans | hard_wta_relation_proto | softwta_positive_only | softhebb_faithful_proto
```

并额外支持：

```text
relation_field_variant = without_preorder | with_preorder
input_mode = input_only | input_output_unpaired
```

### 17.3 objectize.py

负责：

```text
responsibility_to_objects(R, grid, config) -> List[ProtoObject]
```

### 17.4 fixed_template_search.py

复用原多预序实验的固定模板搜索。

要求：

> 不允许因为 SoftWTA 新增执行 primitive。

### 17.5 metrics.py

记录：

```text
exact
pixel_acc
J_train
residual_DL
candidate_count
beam_size
EqK
prototype_utilization
prototype_redundancy
seed_stability
proto_object_coverage
oracle_topK_candidate
oracle_object_coverage
```

---

## 18. 配置示例

### 18.1 实验 A：paper-faithful sanity check

```yaml
experiment_name: softhebb_faithful_sanity_v0
stage: representation_sanity
random_seeds: [0]

tasks:
  source: arc_training
  task_list: configs/s_min_multi_preorder_tasks.txt
  min_train_pairs: 3

loo:
  enabled: true
  input_mode: input_only
  use_heldout_output_for_representation: false

relation_field:
  variant: without_preorder
  patch_radius: 1
  use_color_role: true
  use_raw_color_id: false
  features:
    - color_role_onehot
    - same_color_8mask
    - background_8mask
    - foreground_flag
    - boundary_distance_bucket
    - horizontal_run_length_bucket
    - vertical_run_length_bucket
    - local_transition_count
    - neighbor_color_role_histogram

prototype_bank:
  methods:
    - raw_feature_kmeans
    - hard_wta_relation_proto
    - softwta_positive_only
    - softhebb_faithful_proto
  K: [16]
  tau: [0.1]
  epochs: 1
  adaptive_learning_rate: true
  antihebb_gamma: [0.05]
  normalize_prototypes: true

objectization:
  thresholds: [0.5]
  cc_mode: cc8
  min_area: 1
  max_objects_per_grid: 32

template_search:
  enabled: false

reporting:
  primary:
    - prototype_utilization
    - prototype_redundancy
    - seed_stability
    - perturbation_stability
    - proto_object_coverage
    - oracle_topK_candidate
```

### 18.2 实验 B：小范围鲁棒性与 hybrid 工程验证

```yaml
experiment_name: softhebb_hybrid_template_v0
stage: downstream_engineering
random_seeds: [0, 1, 2]

loo:
  enabled: true
  input_mode: input_only

relation_field:
  variants:
    - without_preorder
    - with_preorder_rank_vector

prototype_bank:
  methods:
    - softhebb_faithful_proto
    - softwta_positive_only
  K: [8, 16]
  tau: [0.1, 0.2]
  adaptive_learning_rate: true

objectization:
  thresholds: [0.5, 0.65]

template_search:
  enabled: true
  beam_k: 8

reporting:
  primary:
    - top1_exact
    - pixel_accuracy
  secondary:
    - J_train
    - candidate_object_count
    - beam_shrink
    - EqK
    - top1_signature_stable_rate
```

---

## 19. 日志格式

每个 fold 记录一行 JSONL：

```json
{
  "task_id": "05f2a901",
  "fold": 0,
  "stage": "representation_sanity",
  "method": "softhebb_faithful_proto",
  "seed": 0,
  "input_mode": "input_only",
  "relation_field_variant": "without_preorder",
  "K_proto": 16,
  "tau": 0.1,
  "antihebb_gamma": 0.05,
  "adaptive_learning_rate": true,
  "patch_radius": 1,
  "num_objects_input": 6,
  "prototype_utilization": 11.4,
  "prototype_redundancy": 0.18,
  "proto_object_coverage": 0.83,
  "oracle_topK_candidate": 0.75,
  "EqK_color_perm_mean": 0.75,
  "EqK_padding_mean": 0.625,
  "top1_exact": null,
  "pixel_acc": null,
  "J_train": null,
  "signature": "translate|boundary_touching|render_all|role_norm|proto_sig_v1"
}
```

同时输出 summary：

```text
summary_by_method.csv
summary_by_task.csv
summary_by_concept.csv
summary_by_perturbation.csv
prototype_diagnostics.csv
```

---

## 20. 预期结果解释

### 情况 A：faithful 无 preorder 明显优于 raw / hard / positive-only

解释：

> SoftHebb 论文机制在 ARC 局部关系场上有真实迁移价值，而不是只在强结构偏置或宽松工程变体下成立。

理论含义：

> 自动结构发现不必完全依赖人工 DSL 扩展；至少在 ARC2 的静态子问题中，可以用局部无监督竞争机制生成候选结构，再由 MDL / residual / perturbation gate 筛选。

### 情况 B：faithful 无 preorder 弱，但 with_preorder hybrid 胜出

解释：

> SoftHebb / SoftWTA 更像补充层，而不是可直接替代强人工偏置的自动发现器。

工程建议：

```text
multi_preorder → relation_field
SoftHebb / SoftWTA → motif/proto-object candidate expansion
MDL/residual → final filtering
```

理论含义：

> 自动结构发现需要“结构化输入 + 自组织发现”，而不是纯无监督聚类。

### 情况 C：inspired 版本有信号，但 faithful 没有

解释：

> 这支持 SoftWTA-inspired 工程路线，但不足以支持 SoftHebb paper transfer。

处理：

* 单独报告 inspired 与 faithful；
* 检查 adaptive learning rate 是否正确实现；
* 检查 winner-only / non-winner 更新是否真的按 faithful 口径实现；
* 不要用 hybrid 结果替代 faithful 结果下结论。

### 情况 D：训练拟合看起来更好，但稳定性与 coverage 没有改善

解释：

> prototype 捕获了局部频率模式，但没有形成任务相关结构，只是在增加搜索噪声。

处理：

* 回到 `input_only + no_preorder + faithful` 的最小协议；
* 先用 representation metrics 判断结构质量，再决定是否接下游模板搜索；
* 收缩超参数网格，不要在最小验证阶段同时扫太多变量。

---

## 21. 反误读声明

1. 本实验不证明 SoftHebb 可以解 ARC。
1. 本实验不证明 prototype 就是语义。
1. 本实验不开放新 DSL primitive。
1. 本实验不允许测试泄漏。
1. 本实验不声称替代多预序。
1. 本实验只验证“自动候选结构生成机制”。
1. 即使实验成功，也只能说明 ARC2 静态结构发现子问题得到增强，不能直接推出 ARC-AGI-3 动态智能体成立。
1. `softhebb_faithful_proto` 与 inspired / hybrid 结果必须分开报告，不能相互替代。

---

## 22. 与可组合信息论 v0.4 的关系

本实验对应 v0.4 中的这一段生命周期：

```text
发现 → 筛选 → 展开 → 提升 → 重写 → 重索引
```

其中它只验证：

```text
发现 → 初步筛选
```

SoftWTA / Hebbian 负责：

```text
局部稳定共现 → 候选结构
```

anti-Hebbian 负责：

```text
候选去冗余 → 避免结构塌缩 / 重复原型
```

MDL / residual / perturbation consistency 负责：

```text
候选结构 → 任务相关结构
```

因此，本实验可以作为一句理论命题的最小工程检验：

> 可组合信息的发现不必一开始依赖全局任务误差信号；局部关系场中的稳定共现，可以通过竞争性自组织形成前语义候选，而这些候选是否具有语义价值，需要再经过任务相关性、扰动稳定性、组合稳定性和重写收益的筛选。

---

## 23. 最小实施顺序

建议按下面顺序做，避免一次性做太大。

### Step 1：冻结主协议

先冻结：

```text
input_only
without_preorder
seed = 0
K = 16
tau = 0.1
threshold = 0.5
patch_radius = 1
```

### Step 2：跑表示学习层基线

先保证 `raw_feature_kmeans / hard_wta_relation_proto` 在 minimal relation field 上跑通。

### Step 3：加入 inspired positive-only

加入 `softwta_positive_only`，验证 soft competition + positive averaging 接口。

### Step 4：加入 faithful SoftHebb

实现 `winner positive + non-winner anti-Hebbian + adaptive learning rate`。

### Step 5：先做 representation sanity check

先比较 utilization / redundancy / seed stability / perturbation stability / oracle coverage。

### Step 6：再接 fixed-template search

只有 Step 5 有正信号时，才比较 exact / pixel / beam shrink。

### Step 7：做 input/output 与 preorder ablation

分别加入：

```text
input_output_unpaired
with_preorder_rank_vector
```

### Step 8：挑战 multi_preorder_v0_baseline

最后再比较：

```text
softhebb_faithful_without_preorder
softhebb_with_preorder
multi_preorder_v0_baseline
```

### Step 9：写分层结论

按三层结论写：

```text
不通过 / 部分通过 / 最小通过 / 强通过
paper transfer 是否成立
engineering value 是否成立
hybrid complement 是否成立
```

---

## 24. 最终判断口径

这组实验的最终问题不是：

> SoftHebb 能不能解 ARC？

而是：

> 在 `input_only + no_preorder` 的 ARC 关系场上，`softhebb_faithful_proto` 是否能比 `raw_feature_kmeans / hard_wta / softwta_positive_only` 更稳定地产生可复用候选？

以及：

> 当这些候选被接到固定模板、固定搜索预算、任务内留一协议下时，它们是否带来真实下游增益；如果加入多预序特征，是否能形成比 `multi_preorder_v0_baseline` 更强的 hybrid 候选生成层？

如果实验 A 为是，它可以被纳入你的理论作为：

```text
自动结构发现的底层候选生成机制
```

如果只有实验 B 为是，它更合理的定位是：

```text
受 SoftHebb 启发的 ARC 前端工程补充层
```

这样写，才能把“论文忠实复现型验证”和“工程启发型 ARC 前端探索”真正切开，也让最终结论更干净、更可信。

[1]: https://github.com/YSystemLabs/struct-agi/blob/main/experiments/multi_preorder_minimal_validation/%E5%A4%9A%E9%A2%84%E5%BA%8F%E5%AF%B9%E8%B1%A1%E5%8F%91%E7%8E%B0%E6%9C%80%E5%B0%8F%E9%AA%8C%E8%AF%81%E5%AE%9E%E9%AA%8C.md "struct-agi/experiments/multi_preorder_minimal_validation/多预序对象发现最小验证实验.md at main · YSystemLabs/struct-agi · GitHub"
[2]: https://openreview.net/forum?id=8gd4M-_Rj1 "Hebbian Deep Learning Without Feedback | OpenReview"
