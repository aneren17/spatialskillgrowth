---
name: without-wearing-a-helmet
description: "检测输入视频或图像中是否发生“未戴安全帽”异常事件。"
---

# 未戴安全帽

## Skill 作用

检测输入视频或图像中是否发生“未戴安全帽”异常事件。

## 工作流选择

- 先检查候选工作流的适用范围、排除条件和能力边界。
- 再结合当前视频或图像证据，判断其工具链是否适合当前输入。
- 历史准确率、证据通过率和调用成本只用于适用性相近时的排序。
- 不要仅根据工作流名称、ID 或工具数量选择工作流。

<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

当前没有可检索工作流。
<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
