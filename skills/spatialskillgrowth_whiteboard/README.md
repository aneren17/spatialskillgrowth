# SpatialSkillGrowth 标准模板

本目录由 `python -m scripts.build_spatialskillgrowth_whiteboard --force` 自动重建，只用于定义 55 个异常
事件类别的标准 Skill 结构、元数据和空工作流目录。请勿在这里编写或保存人工脚本。

所有类别都遵守同一媒体边界：探索只处理图片，`embeddingTool` 可按图片工具参与，图片基线仍为单步
MLLM。冻结视频推理默认根据 `SKILL.md` 和当前抽样帧选出 Top-K 图片工作流，与独立的原视频
embedding 工作流并行执行，再用确定性 OR 规则合并；全工作流模式会执行全部结构合格图片工作流。

人工维护位置是 `skills/spatialskillgrowth/`。实习生应在那里修改 `SKILL.md` 和 `scripts/*.py`，再运行
项目提供的确定性 mock 验证器。验证器不会修改 whiteboard 或生成 `references/workflows/*.json`。
