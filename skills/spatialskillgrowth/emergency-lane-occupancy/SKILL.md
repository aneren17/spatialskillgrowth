---
name: emergency-lane-occupancy
description: "检测输入视频或图像中是否发生“占用应急车道”异常事件。"
---

# 占用应急车道

## Skill 作用

检测输入视频或图像中是否发生“占用应急车道”异常事件。

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

### emergency_lane_occupancy_detector

- ID：`emergency_lane_occupancy_2206144ac1e6`
- 选择条件：本工作流用于检测输入图像中是否存在车辆占用应急车道的异常行为。流程首先利用目标检测模型（yoloTool）识别图像中的车辆及道路标线，随后通过代码沙箱（python_code_sandbox）计算车辆与应急车道边界的结构化空间关系证据，最后由多模态大模型（MLLM）综合视觉特征与空间证据，判定是否发生占用应急车道事件。
- 不选择：不包含视频流或序列帧分析，仅处理单张静态图像输入。; 不检测非车辆物体（如行人、动物、掉落物）占用应急车道的情况，检测器限制为仅针对车辆目标。; 不处理模糊、严重遮挡或无法清晰辨识应急车道标线的低质量图像。; 不涉及对占用时长的统计或历史轨迹回溯，仅基于当前帧进行瞬时状态判定。
- 执行边界：{"event_type": "emergency_lane_occupancy", "media_type": "image", "required_evidence": ["车辆目标的边界框坐标", "应急车道边界的几何定义或检测结果", "车辆与应急车道区域的空间重叠度或距离指标"], "output_format": "binary_classification", "allowed_tools": ["yoloTool", "python_code_sandbox", "MLLM"]}
- 工具链：`yoloTool -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/emergency_lane_occupancy_2206144ac1e6.json`；`scripts/emergency_lane_occupancy_2206144ac1e6.py`

### emergency_lane_occupancy_detector

- ID：`emergency_lane_occupancy_2fff1b65dc02`
- 选择条件：基于静态图像输入，利用 YOLO 目标检测提取视觉特征并结合多模态大语言模型进行语义推理，判定是否存在‘占用应急车道’的异常事件。通过检测车辆与车道线的空间关系收集证据，输出二值化异常判断结果。
- 不选择：视频流、音频或其他非图像类型的媒体输入；需要调用 embeddingTool 进行向量检索的场景；其他类型的交通异常事件（如逆行、超速、事故等）；缺乏清晰车道线或应急车道标识导致检测失效的场景；需要改写或重新分类事件类型的场景。
- 执行边界：支持事件类型仅限 emergency_lane_occupancy；支持媒体类型仅限 image；检测方法为 YOLO 目标检测（建议阈值0.5）+ MLLM 语义判断；输出格式为 binary (是/否)；禁止泛化至其他异常类别；禁止使用 embeddingTool；禁止修改或覆盖人工维护的 SKILL.md 与 scripts/*.py 文件。
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/emergency_lane_occupancy_2fff1b65dc02.json`；`scripts/emergency_lane_occupancy_2fff1b65dc02.py`

### emergency_lane_occupancy_image_baseline

- ID：`emergency_lane_occupancy_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 emergency_lane_occupancy 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/emergency_lane_occupancy_96c9e72153f7.json`；`scripts/emergency_lane_occupancy_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
