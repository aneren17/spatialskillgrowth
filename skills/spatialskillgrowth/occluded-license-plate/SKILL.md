---
name: occluded-license-plate
description: "检测输入视频或图像中是否发生“车牌遮挡”异常事件。"
---

# 车牌遮挡

## Skill 作用

检测输入视频或图像中是否发生“车牌遮挡”异常事件。

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

### occluded_license_plate_detector

- ID：`occluded_license_plate_3e48518cbbb4`
- 选择条件：检测输入图像中是否存在车牌遮挡异常。该工作流首先通过 OCR 工具提取图像中的可见文字信息，随后结合多模态大语言模型分析视觉证据，判断车牌是否被物理遮挡、污损或故意遮蔽，导致无法完整识别。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本）; 图像中未包含车辆或车牌区域; 车牌清晰可见且无任何遮挡、污损或变形; 因光照不足、运动模糊或分辨率过低导致车牌完全不可见（此类属于图像质量问题，而非遮挡异常）; 使用 embedding 工具进行特征提取的场景
- 执行边界：{"required_slots": {"event_type": "occluded_license_plate", "media_type": "image"}, "evidence_requirements": ["必须包含通过 paddleOcrTool 提取的可见文字证据", "必须包含 MLLM 基于图像视觉特征对遮挡状态的定性判断"], "limitations": ["仅适用于静态图像输入", "无法区分遮挡意图（故意遮挡 vs 无意遮挡），仅检测遮挡事实", "依赖 OCR 工具对可见部分的识别能力，若车牌完全不可见则无法通过文字证据辅助判断"]}
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/occluded_license_plate_3e48518cbbb4.json`；`scripts/occluded_license_plate_3e48518cbbb4.py`

### occluded_license_plate_detector

- ID：`occluded_license_plate_74b0c3f20721`
- 选择条件：检测输入图像中是否存在车牌遮挡异常事件。工作流程首先使用 YOLO 工具（检测阈值 0.5）进行目标检测，随后结合多模态大语言模型（MLLM）依据视觉证据判断是否发生车牌遮挡。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非车牌遮挡类的其他异常事件检测
- 执行边界：{"event_type": "occluded_license_plate", "media_type": "image", "required_tools": ["yoloTool", "MLLM"], "constraints": ["禁止使用 embeddingTool", "必须保留 yolotool_0 的 0.5 检测阈值设置", "仅针对车牌遮挡这一特定事件类型进行判断"]}
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/occluded_license_plate_74b0c3f20721.json`；`scripts/occluded_license_plate_74b0c3f20721.py`

### occluded_license_plate_image_detector

- ID：`occluded_license_plate_96c9e72153f7`
- 选择条件：基于多模态大语言模型（MLLM）分析单张图像，检测是否存在车牌遮挡异常事件。通过视觉证据判断车牌区域是否被物体、污渍、角度或人为手段部分或完全遮挡。
- 不选择：非图像类型的媒体输入（如视频流、音频、纯文本或原始视频时序）; 图像中未包含车辆或车牌区域的情况; 车牌清晰可见且无任何遮挡物的正常场景; 需要调用 embeddingTool 进行特征提取的场景; 涉及其他类型异常（如车辆碰撞、行人闯入等）的检测任务
- 执行边界：支持事件类型：occluded_license_plate；支持媒体类型：单张图像（不支持视频时序分析）；证据要求：必须通过 MLLM 工具获取基于可见画面的明确视觉证据；输出格式：二元判断（是/否）；工具约束：仅使用 MLLM 工具，禁止使用 embeddingTool 或其他未列出的工具
- 工具链：`MLLM`
- 资源：`references/workflows/occluded_license_plate_96c9e72153f7.json`；`scripts/occluded_license_plate_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
