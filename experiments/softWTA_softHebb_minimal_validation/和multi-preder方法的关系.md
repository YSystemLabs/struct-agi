# multi-preorder 与 SoftHebb / SoftWTA 的新分层关系

当前 multi-preorder 最适合冻结为一个强基线，但它和 SoftHebb / SoftWTA 的关系要按新分层方案重写。

更准确地说：

> **multi-preorder 不要继续一边改一边和新方法比。它应该先冻结成 `multi_preorder_v0_baseline`，作为 ARC2 前语义对象发现的强人工结构偏置基线。然后把“论文忠实复现型验证”和“工程启发型 hybrid 验证”分开。**

## 1. 为什么还要先冻结 multi-preorder

这样做的好处没有变。

第一，实验会更干净。
如果 `multi_preorder` 同时也在改，结果就会混掉：到底是新方法有效，还是基线变了？

第二，`multi_preorder_v0_baseline` 本身已经有独立理论价值。它代表的是：

```text
人工设计的局部关系 / 预序偏置
→ proto-object candidates
→ 固定模板搜索
```

第三，它现在不只是一条“待替代的方法”，也可以是后续 hybrid 模式中的结构化输入上游。

## 2. 关系现在不是旧的三模式，而是“两层问题 + 一组模式”

旧口径里常被简化成：

```text
Mode A: baseline
Mode B: without_preorder automatic variant
Mode C: with_preorder hybrid variant
```

这个写法在 v0.2 之后已经不够用了，因为它没有区分：

```text
paper-faithful SoftHebb 问题
vs
inspired / hybrid engineering 问题
```

现在应该拆成两层。

### 第一层：paper transfer 问题

这层只回答：

> SoftHebb 论文里的核心机制，能否在 ARC 的 `input_only + without_preorder` 关系场上形成稳定前语义候选？

这一层的主方法不是泛泛的 `SoftWTA`，而是：

```text
softhebb_faithful_proto
```

它必须对应主文档里的严格条件：

```text
input_only
without_preorder
winner-only positive update
non-winner anti-Hebbian update
adaptive learning rate
```

只有这一层的结果，才可以支持：

> SoftHebb 论文方法本身是否迁移到 ARC 前端结构发现。

### 第二层：engineering / hybrid 问题

这层回答的是另一个问题：

> SoftWTA / SoftHebb 风格原型学习，作为 ARC 前端工程层，是否能补强 fixed-template search，或者与 multi-preorder 形成更强 hybrid？

这时才允许出现：

```text
softwta_positive_only
softhebb_with_preorder
softwta_positive_with_preorder
```

它们有价值，但不能反推成：

> SoftHebb 论文方法已经在无结构偏置条件下迁移成功。

## 3. multi-preorder 在新方案里的准确位置

现在 `multi_preorder_v0_baseline` 的位置是固定的：

```text
强结构偏置基线
```

它既不是 faithful SoftHebb 的一部分，也不是 faithful 主协议的输入。

只有在 hybrid 层里，它才可能变成：

```text
relation_field_with_preorder
```

也就是：

```text
Grid
→ multi-preorder relation signal
→ prototype learner
→ proto-object candidates
→ fixed template search
```

这时候它不再是“被替代的旧方法”，而是：

```text
手工结构偏置上游
```

## 4. 应该保留的比较对象

按新口径，最合理的比较对象是下面这组。

```text
Baseline 0:
multi_preorder_v0_baseline

Faithful main:
softhebb_faithful_without_preorder

Inspired engineering:
softwta_positive_without_preorder

Hybrid faithful:
softhebb_with_preorder

Hybrid inspired:
softwta_positive_with_preorder
```

如果只想保留最小闭集，可以先压成四个：

```text
multi_preorder_v0_baseline
softhebb_faithful_without_preorder
softwta_positive_without_preorder
softhebb_with_preorder
```

## 5. 新的结论口径也要同步

原来的说法是：

```text
如果 Mode B > multi-preorder：
说明 SoftWTA 自组织机制本身非常强。

如果 Mode C > multi-preorder 且 Mode C > Mode B：
说明 multi-preorder 是有效结构先验，SoftWTA 能在其上自动发现更高阶 motif。
```

现在要改成更干净的分层表述。

### 情况 A：`softhebb_faithful_without_preorder` 优于 raw / hard / positive-only，并接近或超过 `multi_preorder_v0_baseline`

这说明：

> SoftHebb 论文机制本身在 ARC 前端结构发现里有真实迁移价值。

### 情况 B：`softhebb_faithful_without_preorder` 优于 raw / hard，但仍弱于 `multi_preorder_v0_baseline`

这说明：

> 自动发现机制有价值，但当前还不能替代强人工预序偏置。

### 情况 C：`softhebb_with_preorder` 优于 `multi_preorder_v0_baseline`，但 `softhebb_faithful_without_preorder` 没有明显正信号

这说明：

> 结论只能写成 hybrid engineering 成立，不能写成 SoftHebb paper transfer 成立。

### 情况 D：`softwta_positive_without_preorder` 有信号，但 `softhebb_faithful_without_preorder` 没有

这说明：

> 受 SoftHebb 启发的工程版原型学习有价值，但论文忠实复现版暂时没有得到支持。

## 6. 一句话总结当前二者关系

现在更准确的关系是：

> **`multi_preorder_v0_baseline` 是强结构偏置基线；`softhebb_faithful_without_preorder` 用来回答论文方法本身是否迁移；`softhebb_with_preorder` 和 `softwta_positive_with_preorder` 用来回答手工结构偏置与自动原型学习是否互补。**

所以后续不要再把它写成“multi-preorder vs SoftWTA”这么单层的对抗关系，而应该写成：

```text
baseline
vs faithful automatic discovery
vs inspired engineering variant
vs hybrid complement
```

这才和主实验文档的 v0.2 命名、分层和结论口径一致。
