---
name: lost-manhole-cover
description: "检测输入视频或图像中是否发生“井盖丢失或井盖没盖好”异常事件。"
---

# 井盖丢失或井盖没盖好

## Skill 作用

检测输入视频或图像中是否发生“井盖丢失或井盖没盖好”异常事件。

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

### lost_manhole_cover_detector

- ID：`lost_manhole_cover_428af33cad44`
- 选择条件：基于 YOLO 目标检测（阈值 0.3）与多模态大模型推理，检测输入图像中是否存在井盖丢失或井盖未盖好的异常事件。
- 不选择：非图像类型的媒体输入; 非井盖丢失或未盖好类别的其他异常事件; 需要调用 embeddingTool 的场景; 要求输出详细推理过程而非二值判断的场景
- 执行边界：输入媒体类型限定为图像，事件类型固定为井盖丢失或未盖好；检测逻辑为使用 yolotool 进行初步目标定位，随后通过 MLLM 结合视觉证据进行最终异常判定；输出格式为布尔值（是/否）
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/lost_manhole_cover_428af33cad44.json`；`scripts/lost_manhole_cover_428af33cad44.py`

### lost_manhole_cover_detector

- ID：`lost_manhole_cover_96c9e72153f7`
- 选择条件：基于图像输入（包括视频单帧），利用多模态大模型分析视觉证据，检测是否存在井盖丢失或井盖未盖好的异常事件。
- 不选择：非图像类型的媒体输入; 需要处理原始视频时序的场景; 其他类型的异常事件检测; 需要调用 embeddingTool 的场景
- 执行边界：基于可见画面的明确判断，输出布尔值（是/否），依赖图像中井盖缺失或未正确闭合的视觉特征
- 工具链：`MLLM`
- 资源：`references/workflows/lost_manhole_cover_96c9e72153f7.json`；`scripts/lost_manhole_cover_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
