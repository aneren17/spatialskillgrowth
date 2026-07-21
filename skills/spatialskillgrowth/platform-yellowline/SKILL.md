---
name: platform-yellowline
description: "检测输入视频或图像中是否发生“越过站台黄线”异常事件。"
---

# 越过站台黄线

## Skill 作用

检测输入视频或图像中是否发生“越过站台黄线”异常事件。

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

### platform_yellowline_detector

- ID：`platform_yellowline_96c9e72153f7`
- 选择条件：检测输入图像中是否发生乘客或物体越过站台安全黄线的异常事件。该工作流利用多模态大模型分析视觉证据，判断是否存在违反站台安全界限的行为。
- 不选择：非站台场景的图像（如车厢内部、站外街道）; 未包含站台黄线或黄线模糊不可见的图像; 非图像类型的媒体输入; 不处理原始视频时序，仅依据当前图片证据
- 执行边界：{"event_type": "platform_yellowline", "media_type": "image", "evidence_requirement": "必须通过多模态模型识别站台黄线位置及目标与黄线的相对空间关系", "output_format": "布尔值（是/否）"}
- 工具链：`MLLM`
- 资源：`references/workflows/platform_yellowline_96c9e72153f7.json`；`scripts/platform_yellowline_96c9e72153f7.py`

### platform_yellowline_detector

- ID：`platform_yellowline_a1314fd8a363`
- 选择条件：基于 YOLO 目标检测与多模态大语言模型（MLLM）的视觉证据链，检测图像中是否存在人员或物体越过站台安全黄线的异常行为。
- 不选择：非站台场景（如普通道路、室内走廊无黄线区域）; 未包含清晰站台黄线视觉特征的低分辨率或模糊图像; 非图像类型的媒体输入
- 执行边界：{"event_type": "platform_yellowline", "media_type": "image", "detection_logic": "通过 yoloTool 定位关键视觉元素，结合 MLLM 分析空间位置关系以判定是否越线", "evidence_requirement": "必须包含站台黄线及潜在越线主体的视觉证据"}
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/platform_yellowline_a1314fd8a363.json`；`scripts/platform_yellowline_a1314fd8a363.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
