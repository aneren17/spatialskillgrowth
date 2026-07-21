---
name: cross-barrier
description: "检测输入视频或图像中是否发生“翻越护栏”异常事件。"
---

# 翻越护栏

## Skill 作用

检测输入视频或图像中是否发生“翻越护栏”异常事件。

## 工作流选择

- 探索阶段只处理图片，所有 Skill 工作流禁止调用 `embeddingTool`。
- 图片及视频抽样帧使用同一套 MLLM 或图像工具工作流形成明确的“是/否”判断。
- 冻结视频推理并行执行原视频 `embeddingTool` 和所有检索工作流。
- 汇总使用确定性 OR：任一有效通道判断为“是”，最终结果即为“是”。
- 工作流生命周期只累计图片探索的总指标，不维护跨媒体资格和分媒体指标。
- 先检查候选工作流的适用范围、排除条件和能力边界。
- 再结合当前输入图像或视频抽样帧，判断其工具链是否适合当前输入。
- 历史准确率、证据通过率和调用成本只用于适用性相近时的排序。
- 不要仅根据工作流名称、ID 或工具数量选择工作流。

<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

根据当前输入选择下列工作流；详细参数按需读取对应资源。

### cross_barrier_image_baseline

- ID：`cross_barrier_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 cross_barrier 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/cross_barrier_96c9e72153f7.json`；`scripts/cross_barrier_96c9e72153f7.py`

### cross_barrier_detector

- ID：`cross_barrier_cd9e9a036446`
- 选择条件：基于静态图像输入，利用 GroundingDINO 进行开放词汇实体定位（阈值0.3）并结合多模态大模型（MLLM）分析视觉上下文，检测是否存在人员或物体翻越、跨越护栏的异常行为。
- 不选择：非图像类型的媒体输入（如视频流、音频、纯文本）；涉及护栏但无翻越行为的正常场景（如正常行走、清洁、损坏检测）；未包含护栏或类似物理隔离设施的开放场景；因图像模糊、严重遮挡导致无法清晰识别护栏结构或主体动作的情况；涉及其他类型异常事件（如打架、火灾、入侵等）而非翻越护栏的场景；需要调用 embeddingTool 进行特征提取的任务。
- 执行边界：仅适用于静态图像分析，不处理时序动态变化；检测逻辑依赖 GroundingDINO 对‘护栏’及‘人体/物体’的识别能力以及 MLLM 对空间关系的理解；输出为二元分类（是/否）；检测精度受限于图像质量及模型对遮挡/模糊场景的处理能力。
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/cross_barrier_cd9e9a036446.json`；`scripts/cross_barrier_cd9e9a036446.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
