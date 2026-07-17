# SpatialSkillGrowth 人工可编辑 Skill

本目录是人工 Skill 的唯一维护位置。实习生可以修改各类别目录中的 `SKILL.md` 和
`scripts/<WORKFLOW_ID>.py`，但不应直接维护机器生成的索引。

工作流程：

1. 阅读 `docs/spatialskillgrowth-skill-authoring.md`；
2. 修改当前类别的 `SKILL.md` 和脚本；
3. 运行 `python -m scripts.validate_spatialskillgrowth_skill`；
4. 验证通过后使用 `--install` 更新 `references/workflows` 和 `references/skill.json`。

不要把人工修改写到相邻的 `skills/spatialskillgrowth_whiteboard/`。whiteboard 是可重复生成的只读模板，
运行构建命令时会被整体重置。
