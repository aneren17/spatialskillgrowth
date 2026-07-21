# 探索到底从哪里复制 Skill

本页专门解释 `spatialskillgrowth_whiteboard`、`spatialskillgrowth` 和 run 内三种状态，避免看到同名目录后
误判来源。

## 1. 两个项目级目录

### `skills/spatialskillgrowth_whiteboard/`

这是可重复生成的标准模板：

- 定义 55 个合法异常类别；
- 给每类提供标准目录、基础元数据和空 workflow 目录；
- 不允许人工脚本；
- 运行构建命令会整体删除并重建。

它不再是新探索 run 的 Skill 复制来源。

### `skills/spatialskillgrowth/`

这是人工可编辑来源：

- 实习生修改 `SKILL.md`；
- 实习生编写 `scripts/*.py`；
- 验证器只做确定性 mock，不写 `references/workflows/*.json`；
- 新异常探索和推理 run 从这里复制。

例如 banner 当前有两份人工示例：

```text
skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
skills/spatialskillgrowth/banner/scripts/banner-crop-example.py
```

whiteboard 对应目录没有这两份脚本。

## 2. 新探索 run 的初始化步骤

假设运行：

```python
paths = ExperimentPaths(
    run_id="banner-new-explore",
    problem_classes=["banner"],
)
paths.ensure(config, "explore", resume=False)
```

`ExperimentPaths._initialize_skill_workspace` 现在执行：

1. 用代码中的 `ANOMALY_EVENT_TYPES` 检查 `banner` 是标准类别；
2. 检查 `skills/spatialskillgrowth/banner` 的 SKILL、scripts、references 是否完整；
3. 把整个可编辑 banner Skill 复制到 run 的 active；
4. provisional/archive 复制同一份人工 `SKILL.md`，但不复制 active workflow 和脚本；
5. 写 `SKILLSET.json` 记录真实 `source_root`；
6. 不在 run 内写 `WHITEBOARD.json`。

复制完成后，Retriever 会读取 active 的 `SKILL.md`；探索允许检索 provisional 时还会读取
provisional 的 `SKILL.md`，再结合当前抽帧和候选工作流契约进行 Top-K 排序。运行过程中新增、
晋升、降级或更新工作流时，Repository 只更新 `SKILL.md` 中由
`SPATIALSKILLGROWTH_WORKFLOWS_START/END` 包围的工作流目录；标记区外的人工说明不会被覆盖。

结果：

```text
benchmark_result/.../full/banner-new-explore/skills/
├── SKILLSET.json
├── active/banner/
│   ├── SKILL.md                         # 来自 skills/spatialskillgrowth/banner
│   ├── scripts/banner-ocr-example.py
│   ├── scripts/banner-crop-example.py
│   └── references/workflows/             # 当前仍为空
├── provisional/banner/
│   ├── SKILL.md                         # 同一份人工类别说明
│   ├── scripts/                         # 初始为空
│   └── references/workflows/            # 初始为空
└── archive/banner/
    ├── SKILL.md                         # 同一份人工类别说明
    ├── scripts/                         # 初始为空
    └── references/workflows/            # 初始为空
```

## 3. 为什么示例脚本不会自动成为 active Workflow

Repository 通过 `references/workflows/*.json` 发现可检索 Workflow，而不是只扫描 `scripts/*.py`。因此：

- 两个示例会随可编辑 Skill 目录复制到 run 的 active 目录；
- 因为没有对应 Workflow JSON，它们不会自动进入 Retriever；
- mock 验证器不会替人工创建 JSON 或决定脚本是否发布；
- provisional/archive 只复制类别级 `SKILL.md`，不会复制示例脚本。

如果负责人希望某条人工路线成为正式可检索 Workflow，需要由正式运行侧另行完成永久化。该步骤不属于人工
mock 验证器。

## 4. `SKILL.md` 怎样参与检索

同类别候选通过工具和槽位结构检查后，Retriever 会读取：

```text
skills/active/<event_type>/SKILL.md
```

然后把以下内容一起交给多模态 LLM：

- `SKILL.md` 中的 Skill 作用、工作流选择规则和可选工作流；
- 当前输入图像；冻结视频推理时则使用抽样帧；
- 候选 `references/workflows/*.json` 的机器契约；
- 工作流历史准确率、证据通过率和调用成本。

探索时 LLM 返回最多 Top-K 个工作流 ID；LLM 失败、`SKILL.md` 缺失或返回非法 ID 时，系统退回历史
指标排序。冻结推理不再让 LLM 淘汰候选，而是返回同类别全部结构合格工作流。人工示例如果没有对应
Workflow JSON，仍然不会成为候选。

## 5. `SKILLSET.json` 怎样证明来源

新 run 的文件类似：

```json
{
  "benchmark": "anomaly_detection",
  "description": "Run-local Skill set initialized from editable skills.",
  "source_root": "/home/deep/env/spatialskillgrowth/skills/spatialskillgrowth",
  "problem_classes": [
    {
      "name": "banner",
      "skill_name": "banner",
      "title": "违规横幅检测"
    }
  ]
}
```

排查来源时先看 `source_root`，再比较 active 脚本。不要再用 run 中是否出现 `WHITEBOARD.json` 判断；新 run
不会生成该文件。

## 6. 已存在的旧 run

`--resume` 的原则是不覆盖历史实验，所以已经创建的旧 run 可能仍有：

```text
skills/WHITEBOARD.json
```

这不代表新代码仍从 whiteboard 初始化，只说明该 run 是旧版本创建的。若要验证新初始化逻辑，应使用新
`run-id`，不能用 resume 期待目录结构被重写。

## 7. 动态 benchmark 的例外

非 `anomaly_detection` benchmark 没有对应的人工 55 类 Skill 集，因此会在 run 内动态创建标准 Skill
目录，并写 `SKILLSET.json`。这条兼容路径不影响异常检测来源。
