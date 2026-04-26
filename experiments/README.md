# experiments

本目录用于放置带协议文档、附表配置和结果产物的实验包，而不是一般性的工程脚本。

- 每个实验包应有明确的理论源文件、冻结的附表配置、实现代码与结果产物。
- 当前已整理的 [multi_preorder_minimal_validation](multi_preorder_minimal_validation/多预序对象发现最小验证实验.md) 是理论启发的探索性最小验证包，用于筛选多预序对象发现路线是否值得继续推进；它尚不应视为主理论的正式 Phase A 实验包。
- 该实验包当前还包含一份独立的叙述性结果报告：[multi_preorder_minimal_validation/多预序对象发现最小验证实验报告-0v1.md](multi_preorder_minimal_validation/多预序对象发现最小验证实验报告-0v1.md)，用于固定 canonical rerun 的结论口径。
- 对已经冻结协议的实验包，结果产物应收敛到单一 canonical report，并配套 provenance manifest；避免同一版本号下并列保留多个不同命名的“正式结果”文件。
- `phase1/scripts/` 继续保留工程工具、阶段性辅助脚本与并行探索路线；并非所有脚本目录内容都具有正式实验规范地位。
