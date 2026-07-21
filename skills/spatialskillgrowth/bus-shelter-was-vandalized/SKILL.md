---
name: bus-shelter-was-vandalized
description: "检测输入视频或图像中是否发生“公交站台破坏”异常事件。"
---

# 公交站台破坏

## Skill 作用

检测输入视频或图像中是否发生“公交站台破坏”异常事件。

## 工作流选择

- 探索阶段只处理图片；`embeddingTool` 可按图片工具参与，但图片基线仍为单步 MLLM。
- 图片及视频抽样帧使用同一套图片工作流，可组合 embeddingTool、MLLM 或其他图像工具。
- 冻结视频推理并行执行原视频 `embeddingTool` 和所有检索工作流。
- 汇总使用确定性 OR：任一有效通道判断为“是”，最终结果即为“是”。
- 工作流生命周期只累计图片探索的总指标，不维护跨媒体资格和分媒体指标。
- 已有工作流的“不选择/执行边界”如写明不用 embedding，只约束该工作流的既有工具图，不是框架全局禁令。
- 先检查候选工作流的适用范围、排除条件和能力边界。
- 再结合当前输入图像或视频抽样帧，判断其工具链是否适合当前输入。
- 历史准确率、证据通过率和调用成本只用于适用性相近时的排序。
- 不要仅根据工作流名称、ID 或工具数量选择工作流。

<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

根据当前输入选择下列工作流；详细参数按需读取对应资源。

### bus_shelter_vandalism_detector

- ID：`bus_shelter_was_vandalized_74b0c3f20721`
- 选择条件：检测输入图像中公交站台（候车亭）是否存在人为破坏、涂鸦、结构损毁等异常事件。通过目标检测定位站台，结合多模态大模型分析视觉证据进行判断。
- 不选择：非图像输入；图像中无公交站台；站台处于正常维护、施工、临时遮挡或仅存在自然老化、轻微污渍、天气影响而无破坏迹象；其他类型公共设施破坏；图像模糊或遮挡严重导致无法识别；需调用embeddingTool的场景。
- 执行边界：仅适用于bus_shelter_was_vandalized事件；依赖yoloTool检测（置信度>=0.5）及MLLM语义判断；输出布尔值；禁止使用embeddingTool；不泛化至其他设施或通用异常分类；严格遵循先检测后推理的顺序。
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/bus_shelter_was_vandalized_74b0c3f20721.json`；`scripts/bus_shelter_was_vandalized_74b0c3f20721.py`

### bus_shelter_was_vandalized_image_baseline

- ID：`bus_shelter_was_vandalized_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 bus_shelter_was_vandalized 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/bus_shelter_was_vandalized_96c9e72153f7.json`；`scripts/bus_shelter_was_vandalized_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
