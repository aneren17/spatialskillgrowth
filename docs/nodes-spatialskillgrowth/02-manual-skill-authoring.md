# 手工编写 SpatialSkillGrowth Skill

本文的目标是手工写出一条可校验、可被推理检索的图片 Workflow。手工 Skill 可以像使用其他图片工具一样
调用 `embeddingTool`，但必须传入 `$image` / `runtime.image_path()`。原视频 embedding 仍由框架的独立工作流并行执行。

## 1. 先看完成后的目录

```text
skills/spatialskillgrowth/<skill-name>/
├── SKILL.md
├── scripts/
│   └── <WORKFLOW_ID>.py
└── references/
    ├── skill.json
    └── workflows/
        └── <WORKFLOW_ID>.json
```

例如事件 ID 是 `fire_door_unclosed`，Skill 目录名是 `fire-door-unclosed`。目录名的转换规则是：
小写，非字母数字替换为连字符。

四个文件的职责不同：

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 告诉人和语义检索器：这个类别是什么，各 Workflow 何时适用 |
| `scripts/<id>.py` | 真正执行 `runtime.call` 和 Python 控制流 |
| `references/workflows/<id>.json` | 让 Repository 发现 Workflow，也是检索和结构校验的机器契约 |
| `references/skill.json` | Skill 类别元数据和 Workflow 索引 |

## 2. 先设计证据链

写代码前先回答：

1. 最终的“是/否”由哪一步产生？
2. 哪些中间结果是下游必需输入？
3. 哪一步失败后必须终止，哪一步可以降级？
4. 这条路线不适合什么画面？

三条常见路线：

```text
原图 → MLLM → 是/否

原图 → OCR → MLLM(原图 + OCR 文本) → 是/否

原图 → GroundingDINO → 检测框 → crop → 小图 → MLLM → 是/否
```

工具参数、检测框传递、多 crop 图选择见
[全部工具与中间结果](01-tools-and-intermediate-results.md)。

## 3. 编写 `SKILL.md`

frontmatter 只能且必须包含 `name` 和 `description`：

```markdown
---
name: banner
description: "检测图片或视频抽样帧中是否存在违规横幅。"
---

# 违规横幅检测

## Skill 作用

识别 event_type `banner`。

## 工作流选择

- 文字清晰时优先 OCR + MLLM。
- 横幅占画面很小时优先定位 + crop + MLLM。
- 目标不可见或定位器无法返回框时，不选裁剪路线。
```

`name` 必须与目录名一致。不要把单个样本答案、评测 ID、服务 URL 或一次运行的指标
写进通用 Skill 说明。

`SKILL.md` 中若已有以下标记，不要删除。Repository 会在两个标记之间重建可选
Workflow 目录：

```markdown
<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
...
<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->
```

## 4. 编写 Python Workflow

脚本开头放四个全局对象：

```python
WORKFLOW_ID = "banner-manual-mllm-v1"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("MLLM",)
WORKFLOW_CONTRACT = {...}
```

| 对象 | 规则 |
|---|---|
| `WORKFLOW_ID` | 当前路线唯一 ID，脚本文件名必须是 `<WORKFLOW_ID>.py` |
| `PROBLEM_CLASS` | 精确英文 event ID，与 Skill 目录对应 |
| `DECLARED_TOOLS` | 脚本可能调用的全部工具白名单 |
| `WORKFLOW_CONTRACT` | 这条路线的适用条件、步骤图和参数模板 |

### 一份最小可校验脚本

```python
WORKFLOW_ID = "banner-manual-mllm-v1"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("MLLM",)
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_manual_mllm",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "适合横幅在原图中清晰可见的画面。",
    "exclusions": "不适用于 banner 以外类别；不适用于目标过小或严重遮挡。",
    "capability_boundary": (
        "MLLM 必须返回明确的是或否；"
        "MLLM 失败时当前 Workflow 直接失败。"
    ),
    "steps": [
        {
            "tool_name": "MLLM",
            "args": {
                "file": "$image",
                "filename": "$filename",
                "query": "$question",
                "tool": "qwen36Tool",
            },
            "step_id": "review",
            "depends_on": [],
            "purpose": "检查图片并返回异常判断。",
        }
    ],
}


def solve(runtime, question, image_paths, *, event_type=""):
    review = runtime.call(
        "MLLM",
        {
            "file": runtime.image_path(),
            "filename": runtime.filename(),
            "query": question,
            "tool": "qwen36Tool",
        },
        step_id="review",
        purpose="检查图片并返回异常判断。",
        depends_on=[],
    )
    runtime.require(review, "review")
    return runtime.finish(review)
```

`solve` 的前三个参数必须依次是 `runtime, question, image_paths`。`required_slots`
中的每个名字必须也出现在 `solve` 参数中，例如 `event_type`。

## 5. Contract 每个字段的作用

| 字段 | 作用 |
|---|---|
| `workflow_id` | 与文件名和 `WORKFLOW_ID` 一致 |
| `name` | 给人看的路线名，不是唯一 ID |
| `problem_class` | 精确事件 ID；检索首先按它分类 |
| `required_slots` | 运行前必须注入的变量 |
| `required_tools` | 运行时必须注册的工具集合，也是脚本白名单 |
| `description` | 什么画面适合选这条路线 |
| `exclusions` | 同类任务中哪些画面也不应该选 |
| `capability_boundary` | 哪些证据必须成功，失败时如何处理 |
| `steps` | 工具 DAG、参数模板和步骤用途 |

每个 step：

```python
{
    "tool_name": "paddleOcrTool",
    "args": {"file": "$image", "filename": "$filename"},
    "step_id": "ocr",
    "depends_on": [],
    "purpose": "读取画面文字。",
}
```

- `tool_name` 区分大小写；
- `step_id` 在当前 Workflow 内唯一；
- `depends_on` 只能指向前面已经声明的 step；
- contract 的 `args` 是机器可读模板，`solve` 中的参数应表达同一含义；
- `purpose` 进入轨迹，方便排错，但不会改变执行逻辑。

必须满足以下集合相等：

```text
DECLARED_TOOLS
  = WORKFLOW_CONTRACT["required_tools"]
  = WORKFLOW_CONTRACT["steps"] 中的工具集合
  = solve 中 runtime.call 的工具集合
```

contract 的 step ID 集合也必须等于脚本所有 `runtime.call(..., step_id="...")` 的 step ID 集合。

## 6. 必需步骤和可选步骤

检测框是 crop 的必要输入时：

```python
detect = runtime.call(...)
runtime.require(detect, "detect")
crop = runtime.call(...)
```

OCR 失败后仍允许 MLLM 看原图时：

```python
ocr = runtime.call(...)
if ocr.get("ok"):
    ocr_text = runtime.value(ocr, "content", "")
else:
    ocr_text = ""

review = runtime.call(
    "MLLM",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "query": question + "\nOCR: " + ocr_text,
        "tool": "qwen36Tool",
    },
    step_id="review",
    depends_on=["ocr"],
)
```

即使 OCR 是可选调用，它仍必须出现在 `DECLARED_TOOLS`、contract steps 和 required tools 中；这里的
“可选”只表示它失败后 Workflow 不必立即终止。

## 7. 受限 Python 环境

Skill 脚本不是普通 Python 程序。当前执行器禁止：

```text
import / from import
class
lambda
async / await
with
global / nonlocal
open / eval / exec / __import__
访问以下划线开头的名字或属性
```

可用内建函数包括 `len`、`range`、`min`、`max`、`sorted`、`sum`、`str`、`float`、
`list`、`dict` 等。脚本不能直接读写文件或请求 HTTP，对外操作都应通过已声明工具。

## 8. 运行确定性 mock 校验

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-manual-mllm-v1.py
```

校验顺序：

```text
目录和 SKILL.md frontmatter
  → Python AST 安全限制
  → 全局常量和 solve 签名
  → declared/required/steps/call 工具集合
  → contract/call step_id 集合
  → mock 工具执行 solve
  → 最终值必须是“是”或“否”
```

成功报告的关键形状：

```json
{
  "valid": true,
  "checks": {
    "standard_skill_layout": true,
    "safe_python_ast": true,
    "script_contract": true,
    "mock_execution": true
  },
  "errors": []
}
```

mock 不读取真实媒体、不调用真实接口、不判断真实准确率，也不写入任何 Workflow JSON。因此
`valid=true` 只证明目录、契约和控制流在模拟输入下成立。

## 9. 一条命令部署人工 Workflow

Repository 通过 `references/workflows/*.json` 枚举 Workflow，不会只因为 `scripts/` 中出现 `.py`
就自动使用它。使用部署命令完成转换：

```bash
python -m scripts.deploy_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-manual-mllm-v1.py
```

该命令按顺序完成：

1. 执行与第 8 节相同的目录、契约和 mock 校验；
2. 读取 Python 脚本中的 `WORKFLOW_CONTRACT`；
3. 转成持久化 `WorkflowSpec` JSON，其中适用性字段进入 `applicability`；
4. 写入 `references/workflows/<WORKFLOW_ID>.json`；
5. 将 Workflow 标记为 `status=active`、`mutation_mode=manual`；
6. 更新 `references/skill.json`、根 `SKILLS.json` 和 `SKILL.md` 的可选工作流区。

人工 Workflow 默认视为较高质量，但不会伪造评测指标：

- 部署后直接进入 active，不经过 provisional 晋升；
- 没有真实 trial 时，历史排序使用 0.85 的人工准确率先验和 1.0 的证据率先验；
- 一旦产生至少一次真实 trial，立即改用实际 accuracy/evidence rate；
- 冻结视频推理仍执行全部结构合格 Workflow，质量先验只影响候选顺序，不会排除其他路线。

同 ID JSON 或目标脚本已存在且内容不同时，部署默认拒绝覆盖。确认要用人工版本替换时使用：

```bash
python -m scripts.deploy_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script /path/to/banner-manual-mllm-v1.py \
  --force
```

覆盖已有 JSON 时会保留其真实 `metrics` 和 `source_task_ids`，不会用空指标擦除历史。

`scripts.generate_workflow_python` 是相反方向的 JSON → Python 生成器，不用于部署人工脚本；对人工脚本
使用它的 `--force` 可能覆盖手写控制流。

## 10. 新的推理如何读到修改(找个视频测试下就行，脚本看agents/spatialskillgrowth/anomaly_detection_agent.py里的注释)

部署命令成功生成并同步以下文件后：

```text
SKILL.md
scripts/<id>.py
references/workflows/<id>.json
references/skill.json
```

使用一个新 `run-id` 启动推理。新 run 会从 `skills/spatialskillgrowth/` 复制涉及的类别到
run 内 `skills/active/`。已存在的 run 加 `--resume` 不会刷新这份副本。

如果启动时传入 `--source-run-id`，推理会改用指定探索 run 的 active 快照。这种情况下，
只修改 `skills/spatialskillgrowth/` 不会影响该次推理。

## 11. 常见校验错误

| 报错 | 原因 | 修改 |
|---|---|---|
| 脚本文件名与 `WORKFLOW_ID` 不一致 | ID 只改了一处 | 同步文件名、常量和 contract |
| `PROBLEM_CLASS` 与 Skill 目录不匹配 | 下划线 event ID 与连字符目录混淆 | 例如 `fire_door_unclosed` → `fire-door-unclosed/` |
| `DECLARED_TOOLS` 不一致 | declared、required、steps、call 有差异 | 对比四处工具集合 |
| `step_id` 不一致 | contract 和 call 命名不同 | 对比两处 step ID 集合 |
| `called undeclared tool` | 脚本调用了契约外工具 | 补齐契约或删除调用 |
| `Unsupported Python construct` | 使用 import、lambda、class 等 | 改用受限同步 Python |
| `Step ... failed` | 对 `ok=False` 结果使用了 `require` | 确认它是否真是必需步骤 |
| mock 返回不是“是/否” | `finish` 接收了 OCR/crop/检测器 | 把最终 MLLM 判断交给 `finish` |
| 脚本存在但推理不检索 | 没运行部署命令，或正在 resume 旧 run | 部署脚本并新建 run |

## 12. 提交前检查

```text
[ ] SKILL.md frontmatter 只有 name 和 description
[ ] name 与 Skill 目录名一致
[ ] 脚本文件名 = WORKFLOW_ID + ".py"
[ ] PROBLEM_CLASS 是精确 event_type
[ ] 如调用 embeddingTool，图片 Workflow 使用 `$image` / `runtime.image_path()`，不使用 `$media`
[ ] declared/required/steps/call 工具集合一致
[ ] contract/call step_id 集合一致
[ ] depends_on 只指向前面已定义 step
[ ] 只对不可降级的必需步骤使用 require
[ ] finish 接收真正的“是/否”判断
[ ] 部署命令成功，且内部 mock 校验 valid=true
[ ] 部署结果包含同 ID active/manual Workflow JSON
[ ] 部署命令已同步 references/skill.json 和 SKILL.md 目录
[ ] 使用新 run-id 读取修改后的可编辑 Skill
```
