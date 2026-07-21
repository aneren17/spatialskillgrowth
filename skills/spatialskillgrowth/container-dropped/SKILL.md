---
name: container-dropped
description: "检测输入视频或图像中是否发生“集装箱掉落”异常事件。"
---

# 集装箱掉落

## Skill 作用

检测输入视频或图像中是否发生“集装箱掉落”异常事件。

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

### container_dropped_detector

- ID：`container_dropped_48ef3b2e43a9`
- 选择条件：基于图像输入检测集装箱掉落异常事件。工作流首先使用 GroundingDINO 以 0.3 阈值检测目标，随后利用 UniDepth 估计目标深度，最后结合多模态大语言模型（MLLM）综合视觉与深度证据进行最终判定。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 container_dropped 类别的异常事件; 无法获取目标深度信息的场景
- 执行边界：{"required_event_type": "container_dropped", "required_media_type": "image", "evidence_requirements": ["GroundingDINO 检测结果（阈值 >= 0.3）", "UniDepth 深度估计数据", "MLLM 基于上述证据的综合判断"], "tool_constraints": ["禁止使用 embeddingTool", "必须使用 MLLM 进行最终推理"]}
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/container_dropped_48ef3b2e43a9.json`；`scripts/container_dropped_48ef3b2e43a9.py`

### container_dropped_detector

- ID：`container_dropped_c47dbc69142b`
- 选择条件：基于多模态大模型（MLLM）分析输入图像（包括视频关键帧），检测是否存在集装箱从堆叠位置或运输工具上意外掉落、坠落的异常事件。适用于港口、堆场、物流园区等场景的静态图像异常监控，通过视觉证据判断集装箱是否处于非正常支撑状态（如悬空、倾斜落地、散落或坠落后的静止状态）。
- 不选择：非图像类型的媒体输入（如音频、纯文本）；需要调用 embeddingTool 进行特征提取的任务；需要实时视频流处理或原始视频时序分析的动态场景；非 container_dropped 类别的其他异常事件（如集装箱倾斜未掉落、破损、火灾、泄漏、入侵等）；图像中未包含集装箱或相关基础设施的场景。
- 执行边界：{"supported_media": ["image"], "event_type": "container_dropped", "evidence_source": "visual_analysis", "tool_dependency": ["MLLM"], "output_format": "binary_classification", "constraint": "仅使用 MLLM 进行图像理解与判断，禁止使用 embeddingTool"}
- 工具链：`MLLM`
- 资源：`references/workflows/container_dropped_c47dbc69142b.json`；`scripts/container_dropped_c47dbc69142b.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
