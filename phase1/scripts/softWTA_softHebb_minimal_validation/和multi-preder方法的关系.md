**当前 multi-preorder 最适合冻结为一个强基线**。

更准确地说：

> **multi-preorder 不要继续一边改一边和 SoftWTA 比。它应该先冻结成 `multi_preorder_v0_baseline`，作为 ARC2 前语义对象发现的强人工结构偏置基线。**

这样做有几个好处。

第一，实验会更干净。
你要验证的是：

```text
SoftWTA / SoftHebb 式自组织机制
是否能在不增加 DSL 表达力的前提下
生成接近或超过 multi-preorder 的对象候选
```

如果 multi-preorder 同时也在改，结果就会混掉：到底是新方法有效，还是基线变了？

第二，multi-preorder 本身已经有理论价值。
它代表的是：

```text
人工设计的局部关系/预序偏置
→ proto-object candidates
→ 固定模板搜索
```

而 SoftWTA 代表的是：

```text
局部关系场
→ 竞争性自组织 prototype
→ proto-object candidates
→ 固定模板搜索
```

所以两者正好形成清晰对照：

| 方法                     | 含义            |
| ---------------------- | ------------- |
| cc4 / cc8              | 普通连通块基线       |
| kmeans                 | 普通无监督聚类基线     |
| hard WTA               | 硬竞争原型基线       |
| **multi-preorder**     | **人工结构偏置强基线** |
| SoftWTA                | 自组织软竞争候选生成    |
| SoftWTA + anti-Hebbian | 自组织 + 去冗余候选生成 |

第三，multi-preorder 冻结后，可以作为“结构化输入”的上游。
也就是说，后续不一定非要让 SoftWTA 替代 multi-preorder。更合理的关系可能是：

```text
Grid
→ multi-preorder relation field
→ SoftWTA prototype discovery
→ proto-object candidates
→ fixed template search
```

这样 multi-preorder 是**关系场构造器**，SoftWTA 是**关系原型发现器**。如果这样效果好，说明：

> 人工结构偏置 + 自动原型发现，比纯人工对象发现或纯无监督聚类更强。

我建议你现在明确三种实验模式：

```text
Mode A: multi_preorder_v0_baseline
只跑当前冻结版本，作为强基线。

Mode B: softwta_without_preorder
SoftWTA 只吃基础 relation features，不吃 multi-preorder rank vector。

Mode C: softwta_with_preorder
SoftWTA 吃 multi-preorder relation field / rank vector，测试二者是否互补。
```

结论口径也要分清：

```text
如果 Mode B > multi-preorder：
说明 SoftWTA 自组织机制本身非常强。

如果 Mode C > multi-preorder 且 Mode C > Mode B：
说明 multi-preorder 是有效结构先验，SoftWTA 能在其上自动发现更高阶 motif。

如果 Mode B/C 都 < multi-preorder，但 > kmeans/hardWTA：
说明 SoftWTA 有价值，但当前还不能替代人工预序偏置。

如果都不如普通基线：
说明 SoftWTA 当前只是增加噪声，不适合进入结构发现主链。
```

所以我的建议是：

> **冻结 multi-preorder，别再把它当正在优化的主方法；把它升格为 ARC2 前语义对象发现的“强结构基线”。然后用 SoftWTA 系列去挑战它、补充它、或作为它的下游自组织层。**
