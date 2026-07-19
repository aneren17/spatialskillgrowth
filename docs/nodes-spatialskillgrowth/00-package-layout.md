# 功能目录和依赖边界

`nodes/mem/spatialskillgrowth/` 根目录只保留 `__init__.py`。业务代码按职责放入六个目录：

```text
spatialskillgrowth/
├── core/
│   ├── anomaly_events.py       # 异常事件表和类别元数据
│   ├── models.py               # Task、Workflow、Metric 等数据结构
│   ├── experiment_config.py    # 运行参数和结果目录
│   └── llm_utils.py            # LLM JSON 调用通用函数
├── runtime/
│   ├── tool_contracts.py       # 工具输入输出契约
│   ├── tool_runtime.py         # 工具注册、调用和结果标准化
│   ├── python_skill_runtime.py # 人工/生成脚本执行环境
│   └── workflow_executor.py    # Workflow、基线和 ReAct 执行
├── skills/
│   ├── skill_layout.py         # 标准 Skill 路径规则
│   ├── skill_retriever.py      # 同异常类别候选检索
│   └── human_skill_validation.py
├── growth/
│   ├── param_space.py          # 可探索的工具参数候选
│   ├── mutation.py             # 成功增强和失败修复决策
│   ├── workflow_mutator.py     # 轨迹提取、工作流修改
│   ├── workflow_slots.py       # Workflow 参数引用
│   ├── skill_consolidator.py   # 去重、兼容性判断、合并
│   └── workflow_lifecycle.py   # provisional/active/archive
├── storage/
│   ├── growth_store.py         # SQLite 和 WorkflowRepository
│   └── conversation_trace.py   # 对话式轨迹输出
└── pipeline/
    ├── media_processing.py     # 图片直通和视频抽帧
    ├── task_router.py          # 已知 event_type 下的确定性规划
    ├── evidence_validator.py   # 异常判断和阈值证据门
    ├── answer_evaluator.py     # “是/否”标签比对
    └── orchestrator.py         # 探索与冻结推理总编排
```

## 新代码放在哪里

| 新功能 | 放置目录 | 例子 |
|---|---|---|
| 新增事件别名或事件元数据 | `core/` | 修改 `anomaly_events.py` |
| 新增数据结构或全局运行配置 | `core/` | 修改 `models.py` |
| 新增工具、工具参数或执行规则 | `runtime/` | 修改 `tool_runtime.py` |
| 新增 Skill 发现、目录或人工验收规则 | `skills/` | 修改 `human_skill_validation.py` |
| 新增工作流变异或生命周期规则 | `growth/` | 修改 `mutation.py` |
| 新增数据库表、文件仓库或轨迹格式 | `storage/` | 修改 `growth_store.py` |
| 新增输入预处理、证据门或主流程步骤 | `pipeline/` | 修改 `orchestrator.py` |

命令行参数和数据集解析仍放在 `agents/spatialskillgrowth/`。提示词仍统一放在
`prompt/spatialskillgrowth_prompts.py`，不能写入上述业务模块。

## 依赖方向

主调用方向是：

```text
agents
  → pipeline
      → skills / growth / storage / runtime
          → core
```

同一层允许少量协作依赖，例如 `storage/growth_store.py` 使用
`runtime/workflow_executor.py` 导出 Python Skill。新增代码时应避免让 `core/` 反向导入
`pipeline/` 或 `storage/`，也不要为了缩短 import 路径在根目录建立兼容转发文件。

对外命令没有变化，但内部 Python import 已改成带功能目录的路径。例如：

```python
from nodes.mem.spatialskillgrowth.core.models import TaskRecord
from nodes.mem.spatialskillgrowth.pipeline.orchestrator import ExperimentFactory
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import ToolRuntime
```
