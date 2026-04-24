# Phase 1

本目录对应第一阶段工作区，目标是围绕 ARC-AGI-2 与 ConceptARC 建立最小可证伪的结构学习闭环。

当前状态：Step 1 已冻结，Step 2 已实施到 Step 2b 验收阶段，主文档当前处于“Step 2 已验收冻结，Step 3 准备阶段”。当前稳定结果为：Step 2a 在 Copy1-6 与 Center1-6 上达到 8/12，按“有条件通过”接受；Step 2b 在新增四个概念组上达到 MoveToBoundary 3/6、ExtendToBoundary 2/6、ExtractObjects 2/6，并将 CleanUp 冻结为未收口能力缺口。下一步不是直接启动增长，而是进入 Step 3A，先处理 Step 2 显式移交的残差能力。

说明：Phase 1 的 Step 1/2 代码与实验先形成了当前工程基线；根目录 [docs/draft/可组合信息论.md](../docs/draft/可组合信息论.md) 是后续对这些工程实践的理论综合。当前根目录 [experiments/multi_preorder_minimal_validation](../experiments/multi_preorder_minimal_validation/多预序对象发现最小验证实验.md) 只应视为理论启发的探索性最小验证包，用于筛选多预序路线是否值得继续保留，而不应视为主理论的正式 Phase A 实验包；并行候选路线还包括 [scripts/softWTA_softHebb_minimal_validation/SoftWTA 关系原型发现最小验证实验.md](scripts/softWTA_softHebb_minimal_validation/SoftWTA 关系原型发现最小验证实验.md)。[docs/structure-miner/](docs/structure-miner/README.md) 仅保留旧实验路线的 brainstorming 补充，不作为正式理论或正式实验指导。

## 目录结构

```text
phase1/
├── .gitignore
├── README.md
├── datasets/
│   └── raw/
│       ├── ARC-AGI-2/
│       └── ConceptARC/
├── docs/
│   ├── 第一阶段研究计划-0v1.md
│   ├── 第一阶段算法架构-0v4.md
│   ├── structure-miner/
│   │   └── README.md
│   ├── step1/
│   │   ├── Step1实现设计-0v1.md
│   │   ├── Step1最小接口与任务清单附录-0v1.md
│   │   ├── Step1实现任务分解清单-0v1.md
│   │   └── Step1实验与验收报告-0v1.md
│   └── step2/
│       ├── Step2实现设计-0v1.md
│       ├── Step2最小接口与任务清单附录-0v1.md
│       ├── Step2实现任务分解清单-0v1.md
│       ├── Step2a实验与验收报告-0v1.md
│       └── Step2b实验与验收报告-0v1.md
├── src/
│   ├── step1/
│   └── step2/
├── tests/
│   ├── step1/
│   └── step2/
├── outputs/
│   ├── previews/
│   ├── step1/
│   ├── step2/
│   └── phase9_full/
└── scripts/
    ├── build_render_gallery.py
    └── render_task_json.py
```

## 约定

- `datasets/raw/`：外部下载的原始数据，不纳入 git。
- `docs/`：阶段计划、设计说明、实验记录等文档。
- `docs/structure-miner/`：旧实验路线的 brainstorming 补充与历史材料，不作为正式理论或正式实验规范。
- `docs/step1/`：Step 1 冻结边界、实现设计、接口附录、实验与验收报告。
- `docs/step2/`：Step 2 设计、冻结边界、阶段验收与全量回归说明。
- `src/step1/`：Step 1 冻结实现代码。
- `src/step2/`：Step 2 当前主线实现代码，按 Layer 1-5、runner、utils 组织。
- `tests/step1/`：Step 1 单元测试与接口冻结测试。
- `tests/step2/`：Step 2 单元测试、runner 与报告链路测试。
- `scripts/`：阶段内会反复使用的工具脚本，以及尚在孵化中的并行探索性算法路线。
- `outputs/step1/`：Step 1 debug bundle、attributions、summary 等实验输出。
- `outputs/step2/`：Step 2 中间批次、诊断与局部实验输出。
- `outputs/phase9_full/`：当前 36 任务全量回归产物。
- `outputs/`：渲染结果、gallery、临时实验产物等可再生输出。

## 当前关键入口

- 理论纲领：[../docs/draft/可组合信息论.md](../docs/draft/可组合信息论.md)
- 多预序探索包：[../experiments/multi_preorder_minimal_validation/多预序对象发现最小验证实验.md](../experiments/multi_preorder_minimal_validation/多预序对象发现最小验证实验.md)
- 并行 SoftWTA 探索草案：[scripts/softWTA_softHebb_minimal_validation/SoftWTA 关系原型发现最小验证实验.md](scripts/softWTA_softHebb_minimal_validation/SoftWTA 关系原型发现最小验证实验.md)
- 研究计划：[docs/第一阶段研究计划-0v1.md](docs/第一阶段研究计划-0v1.md)
- 总架构：[docs/第一阶段算法架构-0v4.md](docs/第一阶段算法架构-0v4.md)
- Step 1 实验与验收报告：[docs/step1/Step1实验与验收报告-0v1.md](docs/step1/Step1实验与验收报告-0v1.md)
- Step 2 实现设计：[docs/step2/Step2实现设计-0v1.md](docs/step2/Step2实现设计-0v1.md)
- Step 2b 实验与验收报告：[docs/step2/Step2b实验与验收报告-0v1.md](docs/step2/Step2b实验与验收报告-0v1.md)
- Step 2 全量回归摘要：[outputs/phase9_full/reports/summary.json](outputs/phase9_full/reports/summary.json)

## 脚本

### 1. 一条命令批量渲染并生成 gallery

```bash
python3 phase1/scripts/render_task_json.py phase1/datasets/raw -o phase1/outputs/previews/all --gallery-title "Phase 1 Structured SVG Gallery"
```

这个脚本会：

- 递归扫描 JSON 任务；
- 按数据集和原始子目录结构输出 SVG；
- 在输出目录下自动生成 `index.html` gallery；
- gallery 支持按数据集、子目录分组，以及前端搜索。

### 2. 只重建 gallery

```bash
python3 phase1/scripts/build_render_gallery.py phase1/outputs/previews/all
```

### 3. 快速小样本预览

```bash
python3 phase1/scripts/render_task_json.py phase1/datasets/raw/ARC-AGI-2/data/training -o phase1/outputs/previews/training-sample --max-files 20
```

### 4. 运行 Step 1 批量实验

```bash
python3 -m phase1.src.step1.runner.batch_runner
```

运行后会在 `phase1/outputs/step1/reports/` 下生成 `summary.json`、`summary.md` 与 `attributions.json`。

### 5. 运行 Step 2 全量回归

```bash
python3 -m phase1.src.step2.runner.batch_runner --output-dir phase1/outputs/phase9_full --stage all
```

运行后会在 `phase1/outputs/phase9_full/reports/` 下生成 `summary.json`、`summary.md`、`attributions.json` 与 `regression_flags.json`。若只想跑单阶段或单概念组，可使用 `--stage 2a|2b|all` 和 `--group`。

### 6. 运行 Step 1 测试

```bash
python3 -m unittest discover -s phase1/tests/step1
```

### 7. 运行 Step 2 测试

```bash
python3 -m unittest discover -s phase1/tests/step2 -p "test_*.py"
```

## 本地预览

VS Code 内置浏览器直接打开 `file://.../index.html` 时，可能出现 `ERR_FILE_NOT_FOUND (-6)`。
更稳妥的方式是先在项目根目录起一个本地静态服务，再通过 `http://127.0.0.1` 访问。

### 1. 在项目根目录启动静态服务

```bash
cd /home/laole/ai/structuralist-agi
python3 -m http.server 8765
```

### 2. 在浏览器中打开 gallery

完整预览：

```text
http://127.0.0.1:8765/phase1/outputs/previews/full/index.html
```

如果你重新渲染到别的输出目录，只需要把 URL 后半段替换成对应的 `phase1/outputs/previews/.../index.html` 路径即可。

## 推荐工作流

1. 原始数据只放在 `datasets/raw/`。
2. 研究文档统一写到 `docs/`。
3. 工具脚本统一放到 `scripts/`，避免把临时脚本散落在目录根部。
4. 所有可再生产物都写到 `outputs/`，需要时可整目录清理并重跑。
