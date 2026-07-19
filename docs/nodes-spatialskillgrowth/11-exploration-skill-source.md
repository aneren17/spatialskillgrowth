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
- 验证器安装 `references/workflows/*.json`；
- 新异常探索和推理 run 从这里复制。

例如 banner 人工脚本只存在于：

```text
skills/spatialskillgrowth/banner/scripts/banner-human-review-v1.py
```

whiteboard 对应目录没有这份脚本。

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

结果：

```text
benchmark_result/.../full/banner-new-explore/skills/
├── SKILLSET.json
├── active/banner/
│   ├── SKILL.md                         # 来自 skills/spatialskillgrowth/banner
│   ├── scripts/banner-human-review-v1.py
│   └── references/workflows/banner-human-review-v1.json
├── provisional/banner/
│   ├── SKILL.md                         # 同一份人工类别说明
│   ├── scripts/                         # 初始为空
│   └── references/workflows/            # 初始为空
└── archive/banner/
    ├── SKILL.md                         # 同一份人工类别说明
    ├── scripts/                         # 初始为空
    └── references/workflows/            # 初始为空
```

## 3. 为什么 provisional/archive 不复制人工脚本

三种状态表示“具体 Workflow 的质量状态”，不是三套独立人工知识：

- active：当前可检索执行的路线；
- provisional：探索产生、尚待重复验证的路线；
- archive：低质量、被合并或被容量裁剪的路线。

人工 banner 路线安装时已经进入 active。如果同时复制到 provisional/archive，就会让同一个 workflow ID
出现在三个状态，Retriever 和生命周期无法判断哪个是真实版本。

因此三种状态共享类别级 `SKILL.md`，但 scripts/references 只随 Workflow 状态迁移。

## 4. `SKILLSET.json` 怎样证明来源

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

## 5. 已存在的旧 run

`--resume` 的原则是不覆盖历史实验，所以已经创建的旧 run 可能仍有：

```text
skills/WHITEBOARD.json
```

这不代表新代码仍从 whiteboard 初始化，只说明该 run 是旧版本创建的。若要验证新初始化逻辑，应使用新
`run-id`，不能用 resume 期待目录结构被重写。

## 6. 动态 benchmark 的例外

非 `anomaly_detection` benchmark 没有对应的人工 55 类 Skill 集，因此会在 run 内动态创建标准 Skill
目录，并写 `SKILLSET.json`。这条兼容路径不影响异常检测来源。
