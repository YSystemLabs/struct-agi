# Phase 1

本目录对应第一阶段工作区，目标是围绕 ARC-AGI-2 与 ConceptARC 建立最小可证伪的结构学习闭环。

当前状态：Step 1 已完成“最小闭环已实施冻结”的验收；Step 2 尚未开始。Step 1 当前在 Copy1-6 与 Center1-6 的 12 个训练任务上得到 6 个精确求解、6 个 `ABSTRACTION_FAIL`，结论偏积极但不夸大，意味着主链路已跑通，后续应进入 Step 2 而不是继续在 Step 1 内扩边界。

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
│   └── step1/
│       ├── Step1实现设计-0v1.md
│       ├── Step1最小接口与任务清单附录-0v1.md
│       ├── Step1实现任务分解清单-0v1.md
│       └── Step1实验与验收报告-0v1.md
├── src/
│   └── step1/
├── tests/
│   └── step1/
├── outputs/
│   ├── previews/
│   └── step1/
└── scripts/
    ├── build_render_gallery.py
    └── render_task_json.py
```

## 约定

- `datasets/raw/`：外部下载的原始数据，不纳入 git。
- `docs/`：阶段计划、设计说明、实验记录等文档。
- `docs/step1/`：Step 1 冻结边界、实现设计、接口附录、实验与验收报告。
- `src/step1/`：Step 1 当前实现代码，按 Layer 1-5、runner、utils 组织。
- `tests/step1/`：Step 1 单元测试与接口冻结测试。
- `scripts/`：阶段内会反复使用的工具脚本。
- `outputs/step1/`：Step 1 debug bundle、attributions、summary 等实验输出。
- `outputs/`：渲染结果、gallery、临时实验产物等可再生输出。

## Step 1 关键入口

- 研究计划：[docs/第一阶段研究计划-0v1.md](docs/第一阶段研究计划-0v1.md)
- 总架构：[docs/第一阶段算法架构-0v4.md](docs/第一阶段算法架构-0v4.md)
- Step 1 实验与验收报告：[docs/step1/Step1实验与验收报告-0v1.md](docs/step1/Step1实验与验收报告-0v1.md)
- Step 1 运行摘要：[outputs/step1/reports/summary.json](outputs/step1/reports/summary.json)

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

### 5. 运行 Step 1 测试

```bash
python3 -m unittest discover -s phase1/tests/step1
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

小样本预览示例：

```text
http://127.0.0.1:8765/phase1/outputs/previews/demo/index.html
```

如果你重新渲染到别的输出目录，只需要把 URL 后半段替换成对应的 `phase1/outputs/previews/.../index.html` 路径即可。

## 推荐工作流

1. 原始数据只放在 `datasets/raw/`。
2. 研究文档统一写到 `docs/`。
3. 工具脚本统一放到 `scripts/`，避免把临时脚本散落在目录根部。
4. 所有可再生产物都写到 `outputs/`，需要时可整目录清理并重跑。
