# SoftWTA 关系原型发现最小验证实验

> 版本：v0.1
> 状态：ARC-AGI-2 静态最小验证实验草案
> 目标：验证 SoftHebb / SoftWTA 式局部竞争学习能否作为“前语义结构发现器”，在不扩展 DSL、不增加下游模板表达力的前提下，改善对象候选与固定模板求解表现。

---

## 1. 实验动机

原有多预序对象发现实验验证的是：

> 在固定小型模板池和固定搜索闭集下，多预序对象发现是否比常见分割/聚类基线更稳定地产生可复用对象候选，并改善任务内留一训练对预测表现。

本实验在这个框架上只替换一件事：

> 把“人工枚举的多预序轮廓聚合”扩展为“基于局部关系场的 SoftWTA / SoftHebb 原型发现”。

也就是说，本实验不验证完整 ARC solver，不验证开放式 DSL 扩展，也不验证 ARC-AGI-3 动态智能体。它只验证一个更小的问题：

> 局部关系场中的稳定共现，能否通过软竞争 + Hebbian 聚合 + anti-Hebbian 去冗余，自动形成更有用的 proto-object / proto-relation 候选？

SoftHebb 论文的相关启发是：它提出 multilayer SoftHebb，一种不依赖 feedback、target 或 error signal 的深层学习算法，并强调 soft winner-take-all、Hebbian、unsupervised、online 等机制。论文在 OpenReview 页面中也明确将其定位为通过 Hebbian plasticity 和 soft winner-take-all 网络推进无反馈深度学习。([OpenReview][2])

---

## 2. 最小命题

本实验只检验三个弱命题。

### 命题 A：SoftWTA 原型是否优于普通局部聚类

给定同一组局部关系特征，SoftWTA prototype bank 是否比 k-means / hard WTA / 原始局部特征聚类产生更稳定的对象候选？

### 命题 B：anti-Hebbian 去冗余是否有价值

在同样 prototype 数量下，加入 anti-Hebbian diversity pressure 是否能减少重复原型、降低候选冗余，同时不损害下游 exact / pixel accuracy？

### 命题 C：关系场学习是否能接近或补强多预序

SoftWTA 不是直接替代多预序，而是验证：

> 在多预序/局部关系特征之上，是否可以通过竞争性自组织自动发现更好的 motif / proto-object 候选。

如果 SoftWTA + anti-Hebbian 不能超过当前多预序，但能稳定超过 raw feature clustering / hard WTA，也算部分正结果。

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

本实验验证的是：

> Soft competitive prototype discovery 是否能成为 ARC2 中前语义结构发现的一种有效底层机制。

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

本实验改为：

```text
Grid
→ Local Relation Field
→ SoftWTA Prototype Bank
→ Prototype Activation Maps
→ Proto-Object Candidates
→ Object Graph
→ Fixed Template Search
→ Leave-one-out Evaluation
```

核心变化只发生在：

```text
Local Relation Field → Proto-Object Candidates
```

下游模板池、评分函数、留一协议、扰动协议尽量继承原实验设计。原文中固定模板池包括 `identity / translate / recolor / delete / crop_selected_bbox`，候选程序采用 `select(S); T; R` 骨架，且重点是比较不同对象表示在同一模板池、同一选择器集、同一搜索预算下的稳定解释能力。([GitHub][1])

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
multi_preorder_rank_vector
```

其中：

* `color_role_onehot` 不使用原始颜色编号，而使用颜色角色；
* `same_color_8mask` 表示八邻域同色关系；
* `background_8mask` 表示邻域是否背景；
* `boundary_distance_bucket` 表示到边界的离散距离等级；
* `run_length_bucket` 表示方向连续性；
* `transition_count` 表示局部变化复杂度；
* `multi_preorder_rank_vector` 可以复用原多预序特征输出。

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

---

## 7. SoftWTA Prototype Bank

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

### 7.2 soft responsibility

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

建议温度网格：

```text
τ ∈ {0.05, 0.1, 0.2, 0.5}
```

### 7.3 Hebbian 更新

对每个 prototype：

$$
p_k \leftarrow \mathrm{normalize}\left( p_k + \eta \sum_u r_k(u)(z_u - p_k) \right)
$$

直观含义：

> 经常共同激活的局部关系模式，会被聚合成稳定原型。

### 7.4 anti-Hebbian 去冗余

定义 winner：

$$
k^\star(u) = \arg\max_k r_k(u)
$$

对非 winner prototype 加入弱 repulsion：

$$
p_k \leftarrow \mathrm{normalize}\left( p_k - \eta \gamma\, r_k(u)(z_u - p_k) \right), \quad k \ne k^\star(u)
$$

或使用更稳定的 redundancy penalty：

$$
L_{\mathrm{div}} = \sum_{i \lt j} \mathrm{sim}(p_i, p_j)^2 \cdot \mathrm{overlap}(r_i, r_j)
$$

主实验建议先用 penalty 版本，比较稳定。

### 7.5 冻结策略

每个 LOO fold 中：

1. 只使用拟合集的 $n-1$ 个 train pairs；
2. 使用这些 pairs 的 input 和 output 网格学习 prototype；
3. 冻结 prototype bank；
4. 对留出的 $X_j$ 只做 inference，不用 $Y_j$ 学习 prototype。

禁止使用留出输出 $Y_j$。

可以另做一个 transductive ablation：

```text
允许使用所有 train inputs，但不使用留出 outputs
```

但必须单独报告，不能混入主结果。

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

## 9. 对照组

比较方法集合：

```text
R = {
  cc4,
  cc8,
  bbox,
  raw_feature_kmeans,
  hard_wta_relation_proto,
  softwta_relation_proto,
  softwta_antihebb_relation_proto,
  multi_preorder
}
```

### 9.1 cc4 / cc8

传统连通块基线。

### 9.2 bbox

简单边界框对象基线。

### 9.3 raw_feature_kmeans

使用同样的 $z_u$，但直接 k-means，不使用 soft responsibility，也不使用 Hebbian/anti-Hebbian 更新。

用途：

> 隔离“局部关系特征本身”和“SoftWTA 竞争机制”的贡献。

### 9.4 hard_wta_relation_proto

每个位置只分配给最近 prototype：

$$
r_k(u)\in{0,1}
$$

用途：

> 检验 soft assignment 是否优于 hard assignment。

### 9.5 softwta_relation_proto

使用 soft responsibility + Hebbian 更新。

### 9.6 softwta_antihebb_relation_proto

使用 soft responsibility + Hebbian 更新 + anti-Hebbian 去冗余。

这是本实验主方法。

### 9.7 multi_preorder

原有多预序对象发现方法。

这是强基线，不是必须一开始超过，但必须报告。

---

## 10. 固定下游模板池

下游模板池继承原实验，不允许因 SoftWTA 新增 primitive。记最小模板池为 $\mathcal A_{\min}$，其五个固定一元原语为：`identity`、`translate`、`recolor`、`delete`、`crop_selected_bbox`。

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

对每个方法 $r\in R$：

1. 在 $D_{-j}$ 上学习或枚举对象表示；
2. 在 $D_{-j}$ 上枚举候选程序；
3. 按 $J_{\mathrm{train}}$ 排序；
4. 保留前 $K_{\mathrm{beam}}$ 个候选；
5. 使用 top-1 候选在 $X_j$ 上预测；
6. 与 $Y_j$ 比较。

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

### 14.1 主终点

主终点保持两个：

```text
top-1 exact match count
mean pixel accuracy
```

这和原多预序实验的主终点一致：在冻结任务子集上比较 top-1 exact match 任务数和平均像素准确率，并且必须在同一模板池、同一搜索预算下与所有基线比较。([GitHub][1])

### 14.2 辅终点

辅终点：

```text
J_train_mean
residual_DL
candidate_object_count
beam_shrink
EqK_mean
top1_signature_stable_rate
prototype_redundancy
prototype_utilization
seed_stability
no_regression_count
```

### 14.3 prototype 专属指标

#### utilization

$$
U = \exp\left( -\sum_k \bar r_k \log \bar r_k \right)
$$

表示有效使用了多少 prototype。

#### redundancy

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

---

## 15. 通过标准

定义基线集：

```text
B = {
  cc4,
  cc8,
  bbox,
  raw_feature_kmeans,
  hard_wta_relation_proto
}
```

强基线：

```text
B_strong = {
  multi_preorder
}
```

主方法：

```text
M = softwta_antihebb_relation_proto
```

### 15.1 最小通过

满足以下条件，可认为 SoftWTA 结构发现通过最小验证：

1. 对至少一半普通基线 $b\in B$，有 $W_{\mathrm{em}}(b) \ge 0.5$；
2. 相对普通基线平均 pixel gain 为正，即 $\tfrac{1}{|B|} \sum_{b\in B} \Delta_{\mathrm{acc}}(b) > 0$；
3. 扰动稳定性不低于普通基线平均：

```text
EqK_M >= mean(EqK_B)
```

4. 相比 `softwta_relation_proto`，anti-Hebbian 版本满足：

```text
prototype_redundancy 降低
且 top-1 exact 不下降超过 1 个 fold
```

5. 候选数量不爆炸：

```text
candidate_object_count_M <= 1.25 × mean(candidate_object_count_B)
```

### 15.2 强通过

满足最小通过，并且相对 `multi_preorder` 至少满足二者之一：

```text
top-1 exact match 不低于 multi_preorder
mean pixel accuracy 高于 multi_preorder
```

或：

```text
在 exact/pixel 接近的情况下，EqK / redundancy / seed stability 明显更好
```

### 15.3 部分通过

如果 SoftWTA + anti-Hebbian 明显超过 raw kmeans / hard WTA，但低于 multi-preorder，则结论应写成：

> SoftWTA 是有效的关系原型发现机制，但尚不能替代手工多预序；更适合作为 multi-preorder 的候选生成补充层。

### 15.4 不通过

如果它只提高训练拟合，但：

```text
留一 exact 不升
pixel accuracy 不升
EqK 下降
candidate count 暴涨
seed variance 很大
```

则认为 SoftWTA 原型没有形成稳定结构，只是在增加搜索噪声。

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

### 16.2 soft vs hard

比较：

```text
hard_wta_relation_proto
softwta_relation_proto
```

目的：

> 验证 soft responsibility 是否改善候选后验。

### 16.3 anti-Hebbian

比较：

```text
softwta_relation_proto
softwta_antihebb_relation_proto
```

目的：

> 验证去冗余机制是否降低重复原型和搜索爆炸。

### 16.4 prototype 数量

比较：

```text
K = 8, 16, 32
```

目的：

> 检查结构发现是否依赖过大 prototype bank。

### 16.5 温度

比较：

```text
τ = 0.05, 0.1, 0.2, 0.5
```

目的：

> 检查 soft competition 的尖锐程度。

### 16.6 是否使用多预序特征

比较：

```text
relation_field_without_preorder
relation_field_with_preorder_rank_vector
```

目的：

> 判断 SoftWTA 是替代多预序，还是需要多预序作为前置结构化输入。

---

## 17. 实现闭集

建议新增目录：

```text
phase1/scripts/softwta_relation_proto_validation/
```

文件结构：

```text
softwta_relation_proto_validation/
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
    softwta_v0.yaml
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
fit_softwta(Z_list, config) -> PrototypeBank
infer_responsibility(Z, bank) -> R
```

支持：

```text
method = hard_wta | softwta | softwta_antihebb
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
```

---

## 18. 配置示例

```yaml
experiment_name: softwta_relation_proto_v0
random_seeds: [0, 1, 2]

tasks:
  source: arc_training
  task_list: configs/s_min_multi_preorder_tasks.txt
  min_train_pairs: 3

loo:
  enabled: true
  train_on_outputs_of_fit_pairs: true
  use_heldout_output_for_representation: false

relation_field:
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
    - multi_preorder_rank_vector

prototype_bank:
  methods:
    - raw_feature_kmeans
    - hard_wta_relation_proto
    - softwta_relation_proto
    - softwta_antihebb_relation_proto
  K: [8, 16, 32]
  default_K: 16
  tau: [0.05, 0.1, 0.2, 0.5]
  default_tau: 0.1
  learning_rate: 0.05
  epochs: 10
  antihebb_gamma: [0.0, 0.05, 0.1]
  normalize_prototypes: true

objectization:
  thresholds: [0.35, 0.5, 0.65, 0.8]
  default_threshold: 0.5
  cc_mode: cc8
  min_area: 1
  max_objects_per_grid: 32

template_search:
  primitives:
    - identity
    - translate
    - recolor
    - delete
    - crop_selected_bbox
  selectors:
    - largest_object
    - smallest_object
    - center_object
    - boundary_touching_object
    - unique_color_role_object
    - highest_activation_object
    - lowest_activation_entropy_object
    - unique_prototype_role_object
    - relation_unique_object
  renders:
    - render_all
    - render_selected
    - crop_selected_bbox
  beam_k: 8

scoring:
  lambda_prog: 0.05
  lambda_hyp: 0.05
  lambda_proto: 0.02
  lambda_redun: 0.02

perturbation:
  color_renaming: true
  translation_padding: true
  num_color_permutations: 5
  num_padding_variants: 4

reporting:
  primary:
    - top1_exact
    - pixel_accuracy
  secondary:
    - J_train
    - residual_DL
    - candidate_object_count
    - beam_shrink
    - EqK
    - top1_signature_stable_rate
    - prototype_utilization
    - prototype_redundancy
    - seed_stability
```

---

## 19. 日志格式

每个 fold 记录一行 JSONL：

```json
{
  "task_id": "05f2a901",
  "fold": 0,
  "method": "softwta_antihebb_relation_proto",
  "seed": 0,
  "K_proto": 16,
  "tau": 0.1,
  "antihebb_gamma": 0.05,
  "patch_radius": 1,
  "num_objects_input": 6,
  "num_objects_output": 6,
  "top1_exact": true,
  "pixel_acc": 1.0,
  "J_train": 0.37,
  "residual_DL": 0,
  "beam_size_before": 128,
  "beam_size_after": 8,
  "EqK_color_perm_mean": 0.75,
  "EqK_padding_mean": 0.625,
  "prototype_utilization": 11.4,
  "prototype_redundancy": 0.18,
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

### 情况 A：SoftWTA + anti-Hebbian 明显胜出

解释：

> 局部关系场中的稳定共现确实可以通过竞争性自组织形成有用前语义候选。

理论含义：

> 自动结构发现不必完全依赖人工 DSL 扩展；至少在 ARC2 的静态子问题中，可以用局部无监督竞争机制生成候选结构，再由 MDL / residual / perturbation gate 筛选。

### 情况 B：SoftWTA 胜过 kmeans/hardWTA，但弱于 multi-preorder

解释：

> SoftWTA 是有效补充机制，但多预序的人工结构偏置仍然更强。

工程建议：

```text
multi_preorder → relation_field
SoftWTA → motif/proto-object candidate expansion
MDL/residual → final filtering
```

理论含义：

> 自动结构发现需要“结构化输入 + 自组织发现”，而不是纯无监督聚类。

### 情况 C：SoftWTA 训练好、留一差

解释：

> prototype 捕获了局部频率模式，但没有形成任务相关结构。

处理：

* 加强 perturbation consistency；
* 提高 redundancy penalty；
* 限制 prototype 数量；
* 增加 relation role normalization；
* 检查是否 raw color leakage。

### 情况 D：anti-Hebbian 降低 redundancy 但 exact 下降

解释：

> 去冗余过强，压掉了有用的多解释候选。

处理：

* 降低 $\gamma$；
* 从 hard repulsion 改成 soft penalty；
* 只在晋升阶段做去冗余，不在候选生成阶段做强 repulsion。

---

## 21. 反误读声明

1. 本实验不证明 SoftHebb 可以解 ARC。
2. 本实验不证明 prototype 就是语义。
3. 本实验不开放新 DSL primitive。
4. 本实验不允许测试泄漏。
5. 本实验不声称替代多预序。
6. 本实验只验证“自动候选结构生成机制”。
7. 即使实验成功，也只能说明 ARC2 静态结构发现子问题得到增强，不能直接推出 ARC-AGI-3 动态智能体成立。

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

### Step 1：复刻原协议

先保证原 multi-preorder LOO pipeline 能跑通：

```text
cc4 / cc8 / bbox / multi_preorder
```

### Step 2：加入 raw_feature_kmeans

验证 relation field 输入与 objectization 接口。

### Step 3：加入 hard_wta_relation_proto

验证 prototype activation → object candidate 是否合理。

### Step 4：加入 softwta_relation_proto

比较 soft vs hard。

### Step 5：加入 anti-Hebbian

比较 redundancy、EqK、exact/pixel。

### Step 6：做扰动稳定性

加入 color renaming / padding。

### Step 7：写结论

按三层结论写：

```text
不通过 / 部分通过 / 最小通过 / 强通过
```

---

## 24. 最终判断口径

这个实验的最终问题不是：

> SoftHebb 能不能解 ARC？

而是：

> 在 ARC2 的固定模板、固定搜索预算、任务内留一协议下，SoftWTA + anti-Hebbian 是否能比普通局部聚类更稳定地产生可复用对象候选，并在不扩展 DSL 的前提下改善下游结构解释？

如果答案为是，它就可以被纳入你的理论作为：

```text
自动结构发现的底层候选生成机制
```

而不是：

```text
完整语义理解机制
```

这正好补上你当前理论里最需要的那块：**候选结构不是只能靠人工 DSL 扩展，也可以从前语义关系流中通过局部竞争性自组织自动长出来。**

[1]: https://github.com/YSystemLabs/struct-agi/blob/main/phase1/scripts/multi_preorder_minimal_validation/%E5%A4%9A%E9%A2%84%E5%BA%8F%E5%AF%B9%E8%B1%A1%E5%8F%91%E7%8E%B0%E6%9C%80%E5%B0%8F%E9%AA%8C%E8%AF%81%E5%AE%9E%E9%AA%8C.md "struct-agi/phase1/scripts/multi_preorder_minimal_validation/多预序对象发现最小验证实验.md at main · YSystemLabs/struct-agi · GitHub"
[2]: https://openreview.net/forum?id=8gd4M-_Rj1 "Hebbian Deep Learning Without Feedback | OpenReview"
