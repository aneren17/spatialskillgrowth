---
name: pedestrian-queue
description: "检测输入视频或图像中是否发生“行人排队聚集”异常事件。"
---

# 行人排队聚集

## Skill 作用

检测输入视频或图像中是否发生“行人排队聚集”异常事件。

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

### pedestrian_queue_detector

- ID：`pedestrian_queue_3f406b278470`
- 选择条件：基于静态图像输入，利用人头检测工具提取视觉证据，并结合多模态大语言模型判断场景中是否存在行人排队聚集异常事件。该工作流严格依赖 `paddleHeadDetTool` 提供的检测框作为空间分布证据，由 `MLLM` 综合评估人群排列形态以确认 `pedestrian_queue` 事件。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行语义嵌入的场景; 非 `pedestrian_queue` 类别的其他异常事件检测任务; 无法通过人头检测工具获取有效空间分布证据的极端遮挡或低分辨率场景
- 执行边界：{"supported_event_type": "pedestrian_queue", "supported_media_type": "image", "required_tools": ["paddleHeadDetTool", "MLLM"], "evidence_requirement": "必须包含由 paddleHeadDetTool 生成的人头检测框坐标及数量信息，作为 MLLM 判断排队形态的必要输入", "output_format": "binary_yes_no"}
- 工具链：`paddleHeadDetTool -> MLLM`
- 资源：`references/workflows/pedestrian_queue_3f406b278470.json`；`scripts/pedestrian_queue_3f406b278470.py`

### pedestrian_queue_detector

- ID：`pedestrian_queue_62f634f7afa7`
- 选择条件：基于图像输入，利用人头检测工具（paddleHeadDetTool）识别可见人头，结合代码沙箱（python_code_sandbox）计算结构化证据摘要，最终通过多模态大模型（MLLM）综合视觉证据，判断是否存在‘行人排队聚集’异常事件。
- 不选择：禁止对图像输入调用 embeddingTool; 不适用于非图像类型的媒体输入; 不适用于需要重新分类或改写 event_type 的场景; 不适用于检测除 pedestrian_queue 以外的其他异常事件类别
- 执行边界：{"input_media": "image", "event_type": "pedestrian_queue", "required_tools": ["paddleHeadDetTool", "python_code_sandbox", "MLLM"], "evidence_requirements": "必须包含可见人头检测结果及结构化证据摘要", "output_format": "仅返回‘是’或‘否’"}
- 工具链：`paddleHeadDetTool -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/pedestrian_queue_62f634f7afa7.json`；`scripts/pedestrian_queue_62f634f7afa7.py`

### pedestrian_queue_image_baseline

- ID：`pedestrian_queue_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 pedestrian_queue 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/pedestrian_queue_96c9e72153f7.json`；`scripts/pedestrian_queue_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
