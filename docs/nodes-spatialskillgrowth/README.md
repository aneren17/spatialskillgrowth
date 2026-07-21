# `nodes/mem/spatialskillgrowth` 阅读索引

这组文档只描述当前异常检测实现。2026-07-17 重构后，Omni3D、多 benchmark、动态答案类型和消融入口已删除。

建议顺序：

1. [00-package-layout.md](00-package-layout.md)：六个功能目录的边界和依赖方向；
2. [01-banner-data-walkthrough.md](01-banner-data-walkthrough.md)：一条 banner 数据如何跑完整链路；
3. [03-input-planning-utils.md](03-input-planning-utils.md)：图片探索、视频抽帧和确定性规划；
4. [04-retrieval-execution-runtime.md](04-retrieval-execution-runtime.md)：图片 Skill、视频并行通道和 ReAct；
5. [05-exploration-growth.md](05-exploration-growth.md)：探索如何生成 Skill；
6. [06-store-pipeline-trace.md](06-store-pipeline-trace.md)：持久化和两个 Pipeline；
7. [07-validation-evaluation.md](07-validation-evaluation.md)：阈值证据与人工脚本验证；
8. [08-symbol-index.md](08-symbol-index.md)：当前文件和主要公开符号索引；
9. [09-tool-cookbook.md](09-tool-cookbook.md)：全部运行时工具示例；
10. [10-runtime-and-contract-tutorial.md](10-runtime-and-contract-tutorial.md)：人工脚本运行时；
11. [11-exploration-skill-source.md](11-exploration-skill-source.md)：模板、人工 Skill 与 run 快照；
12. [12-manual-workflow-tutorial.md](12-manual-workflow-tutorial.md)：从设计、编码到安装一条人工 Workflow。

跨模块的写死数值和限制审计见
[../hardcoded-numeric-constraints-audit.md](../hardcoded-numeric-constraints-audit.md)。

主链路只有：

```text
图片探索 + event_type
  → 同类别 Skill 检索
  → 图片工作流 / ReAct
  → 图片指标与生命周期

冻结视频推理 + event_type
  → 抽帧并检索全部结构合格图片工作流
  → 原视频 embedding || 全部图片工作流
  → 证据验收后确定性 OR
```
