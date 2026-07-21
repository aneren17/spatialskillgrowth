---
name: explosion
description: "检测输入视频或图像中是否发生“爆炸检测”异常事件。"
---

# 爆炸检测

## Skill 作用

检测输入视频或图像中是否发生“爆炸检测”异常事件。

## 工作流选择

- 探索阶段只处理图片；`embeddingTool` 可按图片工具参与，但图片基线仍为单步 MLLM。
- 图片及视频抽样帧使用同一套图片工作流，可组合 embeddingTool、MLLM 或其他图像工具。
- 冻结视频推理默认根据本 `SKILL.md` 和当前抽样帧选择 Top-K（默认 2 条）工作流。
- 推理并行执行原视频 `embeddingTool` 和选中的图片工作流；全工作流模式执行全部结构合格路线。
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

### explosion_image_detection_workflow

- ID：`explosion_a8dd7b3d320a`
- 选择条件：基于多模态大语言模型（MLLM）对输入图像（含视频关键帧）进行视觉分析，检测是否存在爆炸异常事件。通过识别火光、浓烟、冲击波或结构损毁等典型视觉特征，依据可见画面证据做出存在性判定，适用于需要快速识别突发爆炸场景的静态图像监控任务。
- 不选择：非图像类型的媒体输入（如原始视频流、音频或纯文本描述）；需要调用 embeddingTool 进行特征提取的场景；非爆炸类异常事件（如火灾蔓延、普通烟雾、交通事故等，除非明确伴随爆炸特征）；需要实时视频帧连续时序分析的场景（本工作流仅针对单帧或静态图像证据）；不进行事件分类或改写，仅针对已确定的爆炸事件进行存在性检测。
- 执行边界：{"event_type": "explosion", "media_type": "image", "required_evidence": ["可见的爆炸火光或火球", "伴随的浓密烟雾或粉尘云", "明显的冲击波视觉效果（如空气扭曲、物体飞溅）", "场景中的结构性破坏痕迹"], "tool_constraints": "仅使用 MLLM 进行图像理解和推理，禁止使用 embeddingTool", "output_format": "布尔值（是/否）", "temporal_scope": "single_frame"}
- 工具链：`MLLM`
- 资源：`references/workflows/explosion_a8dd7b3d320a.json`；`scripts/explosion_a8dd7b3d320a.py`

### explosion_detection_workflow

- ID：`explosion_ca756c4f9788`
- 选择条件：基于开放词汇目标检测、深度估计及多模态大模型推理的爆炸事件检测工作流。该流程首先使用 GroundingDINO 以 0.3 阈值检测潜在爆炸相关视觉特征，随后通过 UniDepth 估计目标深度信息，最后由多模态大模型综合视觉证据判断是否发生爆炸异常。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 explosion 类别的异常检测任务; 不包含爆炸相关视觉特征（如火焰、烟雾、冲击波、碎片等）的静态背景图像
- 执行边界：{"required_tools": ["groundingdino", "unidepth", "MLLM"], "input_constraints": {"media_type": "image", "event_type": "explosion"}, "detection_logic": "依赖 GroundingDINO 的开放词汇检测能力定位目标，结合 UniDepth 的空间深度信息，由 MLLM 进行最终语义判定。不支持非图像输入，不执行 embedding 操作。"}
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/explosion_ca756c4f9788.json`；`scripts/explosion_ca756c4f9788.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
