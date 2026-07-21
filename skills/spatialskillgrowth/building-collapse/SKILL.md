---
name: building-collapse
description: "检测输入视频或图像中是否发生“建筑坍塌”异常事件。"
---

# 建筑坍塌

## Skill 作用

检测输入视频或图像中是否发生“建筑坍塌”异常事件。

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

### building_collapse_detector

- ID：`building_collapse_1bc452328e83`
- 选择条件：针对静态图像输入，通过目标检测（yoloTool）与深度估计（unidepth）结合多模态大模型（MLLM）分析，检测是否存在建筑坍塌（building_collapse）异常事件。该工作流依赖于视觉证据中的结构破坏特征与空间深度信息，适用于需要精确判定建筑物是否发生倒塌场景的自动化检测任务。
- 不选择：非图像类媒体输入（如视频流、音频、纯文本描述）。; 未包含建筑物或结构物的场景（如自然景观、室内无结构背景）。; 需要实时视频流分析或连续帧时序推理的任务。; 依赖 Embedding 工具进行特征提取的场景。; 非 building_collapse 类别的其他异常事件（如火灾、洪水、交通事故等）。
- 执行边界：{"required_event_type": "building_collapse", "required_media_type": "image", "tool_dependencies": ["yoloTool", "unidepth", "MLLM"], "evidence_requirements": ["目标检测结果（阈值 0.5）", "检测目标的深度估计信息", "多模态模型对视觉证据的综合判断"], "output_format": "binary (是/否)"}
- 工具链：`yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/building_collapse_1bc452328e83.json`；`scripts/building_collapse_1bc452328e83.py`

### building_collapse_detector

- ID：`building_collapse_3f5b81b18890`
- 选择条件：基于 YOLO 目标检测（阈值 0.5）与多模态大语言模型（MLLM）的图像分析工作流，专门用于检测输入图像中是否发生建筑坍塌（building_collapse）异常事件，最终输出二分类判断。
- 不选择：非图像类型的媒体输入（如视频、音频、纯文本）；需要调用 embeddingTool 的场景；非建筑坍塌类的其他异常事件（如裂缝、火灾、爆炸、正常施工等）；需要生成自然语言解释而非二分类结果的场景；YOLO 模型未覆盖或无法有效识别的建筑结构类型。
- 执行边界：支持媒体类型：图像；事件类型：建筑坍塌；检测逻辑：YOLO 目标检测（阈值 0.5）结合 MLLM 多模态推理；输出格式：二分类（是/否）；对象限制：严格限定于建筑及其坍塌状态，不可泛化至其他物体。
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/building_collapse_3f5b81b18890.json`；`scripts/building_collapse_3f5b81b18890.py`

### building_collapse_detector

- ID：`building_collapse_96c9e72153f7`
- 选择条件：基于多模态大语言模型（MLLM）分析输入图像，通过识别建筑结构完整性丧失、大规模瓦砾堆积及形态扭曲等视觉证据，判定是否发生建筑坍塌异常事件。
- 不选择：非图像类型的媒体输入; 图像中未包含建筑物或结构物主体; 仅存在轻微裂缝、表面剥落但未导致结构整体失稳或坍塌的场景; 施工中的正常拆除作业; 不处理原始视频时序，仅依据当前图片证据。
- 执行边界：输入媒体限制为图像；目标事件为建筑坍塌；需具备可见的建筑主体结构断裂或倒塌、大面积碎片堆积及形态严重破坏等视觉证据；禁止使用 embeddingTool，必须使用 MLLM 进行视觉特征分析与推理，并基于可见画面给出明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/building_collapse_96c9e72153f7.json`；`scripts/building_collapse_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
