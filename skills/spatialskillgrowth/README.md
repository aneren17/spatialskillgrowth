# SpatialSkillGrowth 人工可编辑 Skill

人工只需要：

1. 修改类别目录中的 `SKILL.md`；
2. 编写 `scripts/<WORKFLOW_ID>.py`；
3. 运行确定性 mock 验证。

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
```

验证器不会调用真实工具、生成 `references/workflows`、修改 `references/skill.json`、更新 `SKILLS.json`
或复制脚本。mock 通过后，由负责人手动复制需要永久保存的文件。

正式运行复制 Skill 后，Retriever 会读取 `SKILL.md` 选择 Top-K 工作流。Repository 会自动更新其中
`SPATIALSKILLGROWTH_WORKFLOWS_START/END` 标记包围的工作流目录，标记外的人工说明保持不变。

相邻的 `skills/spatialskillgrowth_whiteboard/` 是可重复生成的标准模板。验证器不会修改它；手动复制到该
目录的文件会在下一次强制重建 whiteboard 时被覆盖。
