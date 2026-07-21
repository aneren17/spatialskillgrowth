---
name: traffic-accident
description: "检测输入视频或图像中是否发生“交通事故”异常事件。"
---

# 交通事故

## Skill 作用

检测输入视频或图像中是否发生“交通事故”异常事件。

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

### traffic_accident_detector

- ID：`traffic_accident_11bc493538c6`
- 选择条件：基于视觉证据检测图像中是否发生交通事故（traffic_accident）。工作流首先利用 YOLO 工具以 0.5 的置信度阈值检测潜在目标，随后通过 UniDepth 估计检测目标的深度信息以辅助空间理解，最后结合多模态大语言模型（MLLM）综合图像特征、目标检测结果及深度证据，判断是否存在交通事故异常。
- 不选择：非图像类型的媒体输入（如视频、音频或纯文本）。; 需要调用 embeddingTool 进行特征提取的场景。; 非交通事故类别的异常事件检测（如火灾、入侵等，除非工具图显式支持）。; 缺乏清晰视觉证据导致无法判断事故状态的模糊图像。
- 执行边界：{"input_media": "image", "event_type": "traffic_accident", "detection_logic": "YOLO目标检测(阈值0.5) -> 深度估计 -> MLLM综合判断", "output_format": "binary (是/否)", "constraints": "严格依赖工具图定义的步骤，不引入外部未定义工具；仅对交通事故类别有效。"}
- 工具链：`yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/traffic_accident_11bc493538c6.json`；`scripts/traffic_accident_11bc493538c6.py`

### traffic_accident_detector

- ID：`traffic_accident_1900245abeb1`
- 选择条件：基于图像输入，利用 YOLO 目标检测与行人/骑行者专用检测器提取视觉证据，结合多模态大模型判断是否发生交通事故。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非交通事故类别的异常事件检测; 未包含交通参与者或车辆相关视觉元素的场景
- 执行边界：{"required_tools": ["yoloTool", "paddlePedriderDetTool", "MLLM"], "event_type": "traffic_accident", "media_type": "image", "evidence_requirements": "必须通过 yoloTool 和 paddlePedriderDetTool 获取结构化检测框及类别信息，并作为 MLLM 判断的依据", "limitations": "仅适用于静态图像分析，不支持视频流或实时动态检测；检测精度受限于底层视觉模型对遮挡、低光照等复杂环境的鲁棒性"}
- 工具链：`yoloTool -> paddlePedriderDetTool -> MLLM`
- 资源：`references/workflows/traffic_accident_1900245abeb1.json`；`scripts/traffic_accident_1900245abeb1.py`

### traffic_accident_detector

- ID：`traffic_accident_34f138c7ac64`
- 选择条件：基于 YOLO 目标检测（阈值 0.5）与多模态大模型（MLLM）推理，分析输入图像中是否存在交通事故异常事件。通过视觉证据收集与语义判断，确认场景中是否包含符合交通事故定义的视觉特征，最终输出二元判断（是/否）。
- 不选择：非图像类型的媒体输入（如视频、音频、纯文本）；需要调用 embeddingTool 的嵌入向量分析任务；非交通事故类别的其他异常事件检测；未提供有效图像数据或图像内容完全无法解析的情况；要求输出非二元结果（如置信度分数、详细事故描述）或重新分类事件类型的任务。
- 执行边界：仅适用于静态图像分析，不包含视频时序分析或音频证据处理；检测范围严格限定于交通事故，不泛化至其他交通违规或非交通类事故；依赖 YOLO 预训练类别及 0.5 检测阈值的硬性约束；输出格式为二元判断（是/否）。
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/traffic_accident_34f138c7ac64.json`；`scripts/traffic_accident_34f138c7ac64.py`

### traffic_accident_image_detector

- ID：`traffic_accident_96c9e72153f7`
- 选择条件：基于多模态大语言模型（MLLM）对输入图像（包括视频提取的静态帧）进行视觉分析，检测是否存在交通事故异常事件。通过识别车辆碰撞、散落物、交通停滞等视觉特征来判断事故状态。
- 不选择：非图像类型的媒体输入（如纯文本、音频或未转换的视频流）; 需要调用 embeddingTool 进行特征提取的场景; 非交通事故类的其他异常事件（如火灾、洪水、设备故障等）; 模糊、严重遮挡或分辨率过低导致无法辨识车辆及道路状态的图像; 需要处理原始视频时序动态变化的场景。
- 执行边界：{"event_type": "traffic_accident", "media_type": "image", "evidence_requirement": "必须包含可被多模态模型直接感知的视觉证据，如受损车辆、事故现场布局、交通标志异常或紧急车辆出现等", "tool_constraint": "仅使用 MLLM 进行端到端图像理解与判断，禁止使用 embeddingTool"}
- 工具链：`MLLM`
- 资源：`references/workflows/traffic_accident_96c9e72153f7.json`；`scripts/traffic_accident_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
