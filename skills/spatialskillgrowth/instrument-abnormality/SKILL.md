---
name: instrument-abnormality
description: "检测输入视频或图像中是否发生“仪表异常”异常事件。"
---

# 仪表异常

## Skill 作用

检测输入视频或图像中是否发生“仪表异常”异常事件。

## 工作流选择

- 探索阶段只处理图片，所有 Skill 工作流禁止调用 `embeddingTool`。
- 图片及视频抽样帧使用同一套 MLLM 或图像工具工作流形成明确的“是/否”判断。
- 冻结视频推理并行执行原视频 `embeddingTool` 和所有检索工作流。
- 汇总使用确定性 OR：任一有效通道判断为“是”，最终结果即为“是”。
- 工作流生命周期只累计图片探索的总指标，不维护跨媒体资格和分媒体指标。
- 先检查候选工作流的适用范围、排除条件和能力边界。
- 再结合当前输入图像或视频抽样帧，判断其工具链是否适合当前输入。
- 历史准确率、证据通过率和调用成本只用于适用性相近时的排序。
- 不要仅根据工作流名称、ID 或工具数量选择工作流。

<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

根据当前输入选择下列工作流；详细参数按需读取对应资源。

### instrument_abnormality_detector

- ID：`instrument_abnormality_07de9c936d38`
- 选择条件：检测输入图像中是否存在仪表异常事件。该工作流通过 OCR 读取仪表可见文字、使用 GroundingDINO 定位仪表组件并估计其深度，最终结合多模态大模型综合视觉证据判断是否发生仪表异常。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非仪表类设备的异常检测; 需要重新分类或改写 event_type 的任务
- 执行边界：{"event_type": "instrument_abnormality", "media_type": "image", "required_evidence": ["OCR 提取的仪表文字信息", "GroundingDINO 检测到的仪表组件位置（阈值 0.3）", "UniDepth 估计的检测目标深度信息"], "output_format": "是/否"}
- 工具链：`paddleOcrTool -> groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/instrument_abnormality_07de9c936d38.json`；`scripts/instrument_abnormality_07de9c936d38.py`

### instrument_abnormality_image_baseline

- ID：`instrument_abnormality_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 instrument_abnormality 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/instrument_abnormality_96c9e72153f7.json`；`scripts/instrument_abnormality_96c9e72153f7.py`

### instrument_abnormality_detector

- ID：`instrument_abnormality_dedd1e22d850`
- 选择条件：针对静态图像输入，通过 OCR 提取可见文字信息（如读数、标识），并结合多模态大模型分析视觉特征（如指针位置、刻度、指示灯状态），以判定是否存在仪表异常事件。
- 不选择：非图像类型的媒体输入（如纯文本、音频、视频流）；无法通过 OCR 或视觉模型直接观测到的仪表内部机械故障或隐性电路故障；需要实时动态序列分析才能判定的瞬态异常（仅处理单帧静态图像）；图像中仪表区域被严重遮挡、模糊或完全不可见，导致缺少必要 OCR 文字或视觉证据不足以支撑判断的情况。
- 执行边界：仅检测 event_type 为 instrument_abnormality 的异常；依赖 paddleOcrTool 获取文字证据及 MLLM 进行综合视觉推理；输入必须为包含可观测仪表特征的静态图像；输出为二分类结果（binary_yes_no）。
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/instrument_abnormality_dedd1e22d850.json`；`scripts/instrument_abnormality_dedd1e22d850.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
