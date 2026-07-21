---
name: ebike-reverse
description: "检测输入视频或图像中是否发生“非机动车逆行”异常事件。"
---

# 非机动车逆行

## Skill 作用

检测输入视频或图像中是否发生“非机动车逆行”异常事件。

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

### ebike_reverse_detector

- ID：`ebike_reverse_583e438d5c97`
- 选择条件：基于图像输入，利用 GroundingDINO 进行开放词汇目标检测并裁剪区域，结合多模态大模型（MLLM）分析视觉证据（包括车辆朝向与道路行驶方向关系），以判定是否存在非机动车（如电动车、自行车）逆行异常事件。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）；需要调用 embeddingTool 进行特征嵌入的场景；其他类型的交通异常事件（如闯红灯、违停等）或机动车（汽车、卡车等）逆行检测；图像中未包含非机动车、无法识别车辆朝向、无明确道路方向标识或无法判断行驶方向的模糊场景。
- 执行边界：{"required_event_type": "ebike_reverse", "required_media_type": "image", "detection_threshold": 0.3, "evidence_source": "visual_crops_and_groundingdino_detections", "decision_model": "MLLM", "output_format": "binary_yes_no", "constraints": ["仅处理 image 媒体类型", "严格限定 event_type 为 ebike_reverse", "禁止使用 embeddingTool", "必须保留 groundingdino 的 0.3 检测阈值逻辑", "必须使用 MLLM 进行最终语义判断"]}
- 工具链：`groundingdino -> crop_detections -> MLLM`
- 资源：`references/workflows/ebike_reverse_583e438d5c97.json`；`scripts/ebike_reverse_583e438d5c97.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
