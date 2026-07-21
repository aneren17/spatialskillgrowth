---
name: equipment-rust
description: "检测输入视频或图像中是否发生“设备生锈”异常事件。"
---

# 设备生锈

## Skill 作用

检测输入视频或图像中是否发生“设备生锈”异常事件。

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

### equipment_rust_detector

- ID：`equipment_rust_68bfa4a01e72`
- 选择条件：针对静态图像输入，检测工业设备或金属构件表面是否存在生锈异常。工作流首先利用 GroundingDINO 以 0.3 的置信度阈值定位潜在锈蚀区域，随后通过 UniDepth 估算目标深度以辅助空间理解，最后由多模态大语言模型（MLLM）综合视觉证据判断是否发生设备生锈事件。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行语义嵌入的场景; 非设备类物体（如自然景观、生物体、非金属材质表面）的锈蚀或变色检测; 需要实时视频流分析或动态行为识别的场景
- 执行边界：{"supported_event_type": "equipment_rust", "supported_media_type": "image", "detection_logic": "基于开放词汇检测定位、深度估计辅助及多模态推理的综合判断", "constraint": "严格限制于静态图像中的设备生锈检测，不泛化至其他类型的设备故障或非设备类锈蚀"}
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/equipment_rust_68bfa4a01e72.json`；`scripts/equipment_rust_68bfa4a01e72.py`

### equipment_rust_detector

- ID：`equipment_rust_9d74d5206871`
- 选择条件：基于多模态大模型（MLLM）分析输入图像，检测是否存在设备生锈（equipment_rust）异常。通过视觉证据识别金属表面的氧化腐蚀特征，适用于工业设备、管道、结构件等场景的表面状态评估。
- 不选择：非图像类型的媒体输入（如视频、音频、纯文本）；图像中未包含任何可识别的设备或金属结构主体；需要精确量化锈蚀面积百分比、化学成分或详细程度分级的定量分析任务；涉及动态过程（如实时锈蚀生成监控）的连续视频流分析；涉及其他类型异常（如设备破损、漏电、过热等）的检测任务。
- 执行边界：仅支持图像输入；仅判断是否存在设备生锈异常（是/否），不提供锈蚀等级评分、修复建议或量化指标；依赖MLLM基于可见画面的视觉证据直接推理，不涉及语义嵌入工具。
- 工具链：`MLLM`
- 资源：`references/workflows/equipment_rust_9d74d5206871.json`；`scripts/equipment_rust_9d74d5206871.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
