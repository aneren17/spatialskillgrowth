---
name: doors-and-windows-are-damaged
description: "检测输入视频或图像中是否发生“门窗破损”异常事件。"
---

# 门窗破损

## Skill 作用

检测输入视频或图像中是否发生“门窗破损”异常事件。

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

### doors_and_windows_are_damaged_detector

- ID：`doors_and_windows_are_damaged_93f366d102cc`
- 选择条件：本工作流用于检测输入图像中是否存在门窗破损或损坏的异常事件。通过 groundingdino 工具以 0.3 的开放词汇检测阈值定位门窗区域，结合 python_code_sandbox 计算结构化证据摘要，最终由多模态大语言模型（MLLM）依据视觉证据判断是否发生 doors_and_windows_are_damaged 异常。
- 不选择：非图像类型的媒体输入（如视频、音频或纯文本）; 需要调用 embeddingTool 的场景; 门窗外观正常或仅存在轻微污渍、划痕但未达到破损/损坏标准的情况; 图像中未包含门窗主体或门窗区域严重模糊导致无法识别的情况
- 执行边界：{"event_type": "doors_and_windows_are_damaged", "media_type": "image", "required_evidence": ["groundingdino 检测到的门窗实例及其置信度", "python_code_sandbox 生成的结构化证据摘要", "MLLM 基于视觉特征对破损状态的最终判定"], "constraints": ["禁止使用 embeddingTool 处理图像输入", "必须保留 groundingdino 0.3 的检测阈值设置", "最终输出仅为二元判断（是/否）"]}
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/doors_and_windows_are_damaged_93f366d102cc.json`；`scripts/doors_and_windows_are_damaged_93f366d102cc.py`

### doors_and_windows_are_damaged_detector

- ID：`doors_and_windows_are_damaged_f16c7937be91`
- 选择条件：检测输入图像（包括视频关键帧）中是否存在门窗破损或损坏的异常事件。利用多模态大语言模型（MLLM）分析视觉特征，识别门或窗结构上的物理损伤证据，如破碎、裂痕、缺失部件或严重变形。
- 不选择：非图像类型的媒体输入（如纯文本、音频或连续视频流）; 未包含门或窗主体的图像场景; 门窗外观正常但功能异常（如无法开关）且无可见物理破损的情况; 需要调用 embeddingTool 进行语义嵌入处理的场景; 需要区分具体破损原因（如人为破坏 vs 自然灾害）的细粒度归因任务
- 执行边界：支持事件类型：doors_and_windows_are_damaged; 支持媒体类型：静态图像（含视频单帧）; 所需证据：视觉可见的物理结构损坏（如玻璃破碎、框架断裂、铰链脱落等）; 工具约束：仅使用 MLLM 进行视觉推理，禁止使用 embeddingTool; 输出格式：布尔值（是/否）
- 工具链：`MLLM`
- 资源：`references/workflows/doors_and_windows_are_damaged_f16c7937be91.json`；`scripts/doors_and_windows_are_damaged_f16c7937be91.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
