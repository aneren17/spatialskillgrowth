# `nodes/mem/spatialskillgrowth` 阅读索引

这组文档只描述当前异常检测实现。2026-07-17 重构后，Omni3D、多 benchmark、动态答案类型和消融入口已删除。

建议顺序：

1. [00-package-layout.md](00-package-layout.md)：六个功能目录的边界和依赖方向；
2. [01-banner-data-walkthrough.md](01-banner-data-walkthrough.md)：一条 banner 数据如何跑完整链路；
3. [03-input-planning-utils.md](03-input-planning-utils.md)：图片、视频和确定性规划；
4. [04-retrieval-execution-runtime.md](04-retrieval-execution-runtime.md)：Skill、embedding 基线、ReAct；
5. [05-exploration-growth.md](05-exploration-growth.md)：探索如何生成 Skill；
6. [06-store-pipeline-trace.md](06-store-pipeline-trace.md)：持久化和两个 Pipeline；
7. [07-validation-evaluation.md](07-validation-evaluation.md)：阈值证据与人工脚本验证；
8. [08-symbol-index.md](08-symbol-index.md)：当前文件和主要公开符号索引；
9. [09-tool-cookbook.md](09-tool-cookbook.md)：全部运行时工具示例；
10. [10-runtime-and-contract-tutorial.md](10-runtime-and-contract-tutorial.md)：人工脚本运行时；
11. [11-exploration-skill-source.md](11-exploration-skill-source.md)：模板、人工 Skill 与 run 快照。

主链路只有：

```text
媒体 + event_type
  → 抽帧
  → 同类别 Skill 检索
  → Skill / embedding 基线 / ReAct
  → event_type + is_anomaly + threshold 验证
```
