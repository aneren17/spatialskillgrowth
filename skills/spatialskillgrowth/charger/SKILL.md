---
name: charger
description: "检测输入视频或图像中是否发生“充电器未归位”异常事件。"
---

# 充电器未归位

## Skill 作用

检测输入视频或图像中是否发生“充电器未归位”异常事件。

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

### charger_image_baseline

- ID：`charger_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 charger 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/charger_96c9e72153f7.json`；`scripts/charger_96c9e72153f7.py`

### charger_unreturned_detection

- ID：`charger_e209f7624e92`
- 选择条件：基于多模态大语言模型（MLLM）分析静态图像中的视觉证据，检测充电器是否处于未归位状态（即未在指定归位区域或处于非收纳状态），仅输出二值判断结果。
- 不选择：非图像类型的媒体输入（如视频流、音频、纯文本）; 需要调用 embeddingTool 进行特征提取的场景; 涉及充电器物理损坏、线路断裂、电气安全等硬件故障检测; 需要动态时序分析、连续监控或历史记录查询的场景; 需要识别充电器品牌、型号、序列号或进行个体归属/配对分析的场景; 需要输出详细异常原因、置信度分数或后续操作建议的场景。
- 执行边界：{"input_modality": "image", "event_type": "charger", "anomaly_definition": "充电器未归位", "reasoning_method": "visual_evidence_based_mllm", "output_format": "binary_classification", "constraint": "仅进行状态判定，不进行原因分析或特征提取"}
- 工具链：`MLLM`
- 资源：`references/workflows/charger_e209f7624e92.json`；`scripts/charger_e209f7624e92.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
