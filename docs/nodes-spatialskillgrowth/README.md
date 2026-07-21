# SpatialSkillGrowth 新人入门

这组文档只保留三件事：项目如何运行、工具如何传递中间结果、如何手工编写 Skill。
如果你完全不了解项目，先读本页，再按顺序读：

1. [全部工具与中间结果](01-tools-and-intermediate-results.md)；
2. [手工编写 Skill](02-manual-skill-authoring.md)。

## 1. 先区分三个概念

| 概念 | 是什么 | 存在哪里 |
|---|---|---|
| Skill | 一个异常类别的说明和工作流集合，例如 `banner` | `skills/spatialskillgrowth/banner/` |
| Workflow | 一条具体工具路线，例如 OCR → MLLM | `references/workflows/<id>.json` + `scripts/<id>.py` |
| Run 快照 | 某次探索或推理实际使用的 Skill 副本 | `benchmark_result/.../<run-id>/skills/` |

`SKILL.md` 不是可执行程序。Workflow JSON 负责让检索器发现和筛选路线，同 ID
Python 脚本负责真正执行。JSON 是被检索的必要条件；如果没有同 ID 脚本，框架会按 JSON
生成通用顺序脚本。因此，想保留人工编写的分支和降级逻辑时，JSON 和 Python 脚本必须一起存在。
人工脚本可使用 `python -m scripts.deploy_spatialskillgrowth_skill` 完成校验、JSON 转换和索引同步。

## 2. 项目从哪里进入

```text
agents/spatialskillgrowth/
├── online_data.py               # 把媒体和 event_type 变成 Task
├── exploration_agent.py         # 有标签图片探索
└── anomaly_detection_agent.py   # 冻结 Skill 推理

nodes/mem/spatialskillgrowth/
├── core/       # 事件类别、数据结构、运行配置
├── pipeline/   # 图片/视频预处理、总编排、证据验收
├── skills/     # Skill 目录规则、检索、人工脚本校验
├── runtime/    # 工具契约、返回值归一化、Workflow 执行
├── growth/     # 探索产生、修改、合并和晋升 Workflow
└── storage/    # SQLite、轨迹和 Skill 文件持久化

tools/basicTools/             # 12 个真实工具接口
skills/spatialskillgrowth/    # 人工维护的可编辑 Skill 源
prompt/                       # LLM 提示词
scripts/                      # 白板构建、mock 校验和辅助脚本
```

主依赖方向是：

```text
agents → pipeline → skills / runtime / growth / storage → core
```

## 3. 图片探索怎么跑

```text
图片 + event_type + 标签
  → 生成确定性工具计划（排除 embeddingTool）
  → 检索同 event_type 的已有 Workflow
  → 执行图片 Workflow，必要时使用 ReAct
  → 用标签和证据验收结果
  → 产生/修改 Workflow，累计指标并进入 active/provisional/archive
```

探索只接受图片。`embeddingTool` 对图片的输出不可用，因此探索和 Skill 工作流都
不得调用它。

## 4. 视频推理怎么跑

```text
原始视频 + event_type
  → 默认 1 fps 抽帧，最多 12 帧
  → 取该 event_type 的全部结构合格 active Workflow
  → 并行：
       A. 原始视频 → embeddingTool
       B. 抽样帧 → 所有图片 Workflow
  → 每个通道先做证据验收
  → 确定性 OR：任一有效结果为“是”则最终为“是”；全部有效结果为“否”才返回“否”
```

这里有两个边界：

- embedding 是框架在视频推理外层固定加入的通道，不是可检索 Skill；
- 图片 Workflow 对视频的理解只来自最多 12 张抽样帧，它本身不理解连续时序。

## 5. 一次工具链如何传数据

```text
runtime.call(检测工具)
  → 统一 result 字典
  → runtime.value(result, "detections", [])
  → runtime.call(crop, {"detections": boxes})
  → runtime.value(crop, "image_refs", [])
  → 选择其中一张
  → runtime.call("MLLM", {"file": selected_image})
  → runtime.finish(mllm_result)
```

`call` 执行并记录工具，`value` 取统一字段，`require` 在必需步骤失败时终止当前
Workflow，`finish` 只把最终工具文本归一成短答案。详细见
[全部工具与中间结果](01-tools-and-intermediate-results.md)。

## 6. 可编辑 Skill 与运行快照

`skills/spatialskillgrowth/` 是人工维护源。新 run 创建时，会把当前涉及的类别复制到 run 的
`skills/active/`。所以：

- 修改可编辑源后，新建 `run-id` 才会自动取到新内容；
- 旧 run 配合 `--resume` 不会重新复制源 Skill；
- 使用 `--source-run-id` 时，推理会快照指定探索 run 的 active Skill，而不是再读
  当前可编辑目录。

`skills/spatialskillgrowth_whiteboard/` 是可重建的空模板，不要在其中保存人工脚本。

## 7. 最接近源代码的位置

| 想核对的行为 | 源文件 |
|---|---|
| 视频抽帧 | `pipeline/media_processing.py` |
| 探索/推理总流程 | `pipeline/orchestrator.py` |
| 视频并行 OR | `runtime/workflow_executor.py` |
| 工具契约 | `runtime/tool_contracts.py` |
| 工具返回值归一化 | `runtime/tool_runtime.py` |
| `call/value/require/finish` | `runtime/python_skill_runtime.py` |
| 人工 Skill 校验 | `skills/human_skill_validation.py` |
| Workflow 发现与持久化 | `storage/growth_store.py` |
