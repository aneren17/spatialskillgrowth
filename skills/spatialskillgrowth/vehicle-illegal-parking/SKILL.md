---
name: vehicle-illegal-parking
description: "检测输入视频或图像中是否发生“车辆违停”异常事件。"
---

# 车辆违停

## Skill 作用

检测输入视频或图像中是否发生“车辆违停”异常事件。

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

### vehicle_illegal_parking_detector

- ID：`vehicle_illegal_parking_1310756365ce`
- 选择条件：基于静态图像输入，通过 YOLO 检测车辆目标与 PaddleOCR 提取场景文字，结合多模态大模型综合判断是否存在车辆违停异常事件。
- 不选择：非图像类型的媒体输入（如视频流、音频、纯文本描述）; 需要调用 embedding 工具的场景; 动态交通流分析或实时视频帧序列处理; 非车辆违停类别的其他异常检测任务; 无法通过 OCR 或 YOLO 获取有效视觉证据的模糊或遮挡严重图像
- 执行边界：{"input_media": "image", "event_type": "vehicle_illegal_parking", "required_evidence": ["yoloTool 输出的车辆检测框及置信度", "paddleOcrTool 输出的可见文字内容"], "decision_output": "binary (是/否)"}
- 工具链：`paddleOcrTool -> yoloTool -> MLLM`
- 资源：`references/workflows/vehicle_illegal_parking_1310756365ce.json`；`scripts/vehicle_illegal_parking_1310756365ce.py`

### vehicle_illegal_parking_image_baseline

- ID：`vehicle_illegal_parking_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 vehicle_illegal_parking 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/vehicle_illegal_parking_96c9e72153f7.json`；`scripts/vehicle_illegal_parking_96c9e72153f7.py`

### vehicle_illegal_parking_detector

- ID：`vehicle_illegal_parking_a7a05ae6f129`
- 选择条件：针对静态图像输入，通过OCR识别交通标识文字、YOLO检测车辆及环境物体，结合代码沙箱计算结构化证据，最终由多模态大模型判定是否发生车辆违停异常。
- 不选择：非图像类型的媒体输入; 需要视频时序分析的场景; 涉及其他类型异常事件（如交通事故、行人闯入等）的检测; 未包含交通标识或车辆可视区域的图像
- 执行边界：{"required_evidence": ["通过OCR提取的交通禁令标识文字（如禁止停车标志）", "通过YOLO检测到的车辆实例及其位置信息", "车辆与交通标识或禁停区域的空间关系证据"], "constraints": ["仅支持单帧图像分析", "依赖工具图中定义的OCR、目标检测和代码执行步骤", "不泛化至其他违停定义或动态交通场景"]}
- 工具链：`paddleOcrTool -> yoloTool -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/vehicle_illegal_parking_a7a05ae6f129.json`；`scripts/vehicle_illegal_parking_a7a05ae6f129.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
