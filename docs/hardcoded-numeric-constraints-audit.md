# 项目写死数值约束审计

审计日期：2026-07-19

本文只做盘点，不修改任何代码。目标是找出那些会限制候选数量、步骤数量、文本长度、视频帧数、超时、
并发、阈值或资源使用的数值，供后续逐项决定：

- 保留；
- 删除限制；
- 改为配置项；
- 只调整默认值；
- 删除所属的旧代码。

## 1. 审计范围和判断标准

扫描范围：

```text
agents/
config/
model/
nodes/mem/spatialskillgrowth/
server/
skills/
tools/
scripts/
mdconvert.py
utils.py
```

共扫描 67 个 Python 源文件和相关 Shell/Workflow 文件，AST 找到 422 个数值字面量。本文没有把所有
`0`、`1` 都列为问题，而是保留以下几类：

1. 改变算法搜索空间或执行次数；
2. 截断输入、输出、上下文或名称；
3. 限制视频、上传文件、并发、超时或内存；
4. 固定检测阈值、采样参数或概率先验；
5. 名义上在配置对象中，但命令行、环境变量和 API 都不能修改；
6. 虽然当前不在主链路，但仍留在仓库中的旧工具或辅助脚本限制。

下列数字不作为“待删除限制”：

- 数组第一项、最后一项、中间项等索引；
- 毫秒与秒的 `1000` 单位换算；
- JSON `indent=2`；
- HTTP 400、500、502 等协议状态码；
- bbox 必须有 4 个坐标这类数据格式；
- 计数器从 0 开始；
- 测试中的期望值。

## 2. 标记说明

| 标记 | 含义 |
|---|---|
| `硬编码` | 调用方无法通过现有配置修改 |
| `半可调` | 有类属性或函数参数，但主入口没有暴露 |
| `已可调` | 已有 CLI 或环境变量 |
| `协议约束` | 来自文件格式、坐标格式、HTTP 或模型接口 |
| `非主链路` | 当前异常检测运行不会调用，或只用于演示/旧工具 |

建议栏只是审计意见，不代表必须修改。

除非表格中写了完整路径，否则 `core/`、`growth/`、`pipeline/`、`runtime/`、`skills/` 和
`storage/` 都是相对于 `nodes/mem/spatialskillgrowth/` 的路径。

## 3. 最值得优先确认的限制

| ID | 当前限制 | 为什么优先 |
|---|---|---|
| P01 | 图片探索/图片推理候选 Workflow 最多执行 3 条 | 即使 `workflow_top_k` 调大，串行执行器仍强制裁到 3；冻结视频推理不受此限制 |
| P02 | 自动提取工作流最多保留 4 个证据步骤和 1 个 MLLM | 会直接丢弃探索轨迹中的其他有效工具 |
| P03 | 每次 mutation 最多组合 3 个 atom，成功只留 2 个候选、失败只留 3 个 | 直接限制 Skill 探索空间 |
| P04 | 每类 active Workflow 最多 12 条 | 超出后自动归档 |
| P05 | 晋升、降级、归档的试验次数和准确率全部固定 | 只有 10 条数据时影响尤其大 |
| P06 | 视频默认最多 12 帧 | 长视频或关键异常很短时可能漏掉 |
| P07 | 多处上下文截断为 6000 或 12000 字符 | 会静默丢失前部轨迹 |
| P08 | 工具提示只保留 8 个单词 | 中文提示按空格分词时行为不稳定 |
| P09 | GroundingDINO/SAM/YOLO 的探索阈值只允许少数离散值 | 搜索空间被固定菜单限制 |
| P10 | 工具 HTTP 超时固定 600 秒，Sandbox 固定 10 秒 | 一个太长，一个可能太短 |
| P11 | LLM 限流只重试 3 次，每次固定等待 10 秒 | 无指数退避，也不能按服务配置 |
| P12 | FastAPI 的辅助工具覆盖阈值固定为 1.0 | 这是明确业务规则，但目前不能配置 |

## 4. 探索配置：集中定义但主入口不可调

位置：

- `nodes/mem/spatialskillgrowth/core/experiment_config.py:36-47`
- `nodes/mem/spatialskillgrowth/core/experiment_config.py:59-60`
- `agents/spatialskillgrowth/exploration_agent.py:47-55`
- `agents/spatialskillgrowth/anomaly_detection_agent.py:67-72`
- `server/anomaly_detection_server.py:160-163`

`ExperimentConfig` 看起来是配置对象，但 `build_experiment_config()` 只接收 `seed`。CLI 和 FastAPI
也只把 seed 传进去。所以下列字段目前属于“半可调”：写 Python 时可以改，正常运行入口不能改。

| ID | 字段和值 | 实际影响 | 类型 | 建议 | 你的决定 |
|---|---|---|---|---|---|
| C01 | `workflow_top_k=3` | 图片探索只返回前三条 Workflow；冻结视频推理返回全部结构合格 Workflow | 半可调 | 暴露 CLI/env；是否取消要结合延迟 | |
| C02 | `success_candidate_budget=2` | 一次成功样本最多执行 2 个增强候选 | 半可调 | 小数据下可能过窄，建议可调 | |
| C03 | `failure_candidate_budget=3` | 一次失败样本最多执行 3 个修复候选 | 半可调 | 建议可调或允许 `None` 表示不限 | |
| C04 | `active_cap_per_class=12` | 每类 active 超过 12 后触发 Pareto 归档 | 半可调 | 建议允许关闭 cap | |
| C05 | `provisional_promotion_trials=1` | 至少 1 次试验、1 次正确、1 次证据通过即可晋升 | 半可调 | 当前针对每类 10 条图片的小样本探索放宽 | |
| C06 | `provisional_validation_trials=2` | 每条 provisional 最多拿 2 条未见样本验证 | 半可调 | 可考虑使用全部可用未见样本 | |
| C07 | `provisional_validation_candidates_per_class=4` | 每类只验证前 4 条 provisional | 半可调 | 建议可调或不限 | |
| C08 | `provisional_archive_trials=5` | provisional 至少试 5 次才可能归档 | 半可调 | 需要结合总样本数 | |
| C09 | `active_demotion_trials=3` | active 至少试 3 次才可能降级 | 半可调 | 建议可调 | |
| C10 | `promotion_accuracy=0.5` | 晋升要求准确率和证据率都不低于 0.5 | 半可调 | 当前针对小样本探索略微放宽 | |
| C11 | `demotion_accuracy=0.4` | active 低于 0.4 会降回 provisional | 半可调 | 建议与样本数一起设计 | |
| C12 | `archive_accuracy=0.25` | provisional 低于 0.25 会归档 | 半可调 | 建议与置信区间或最小样本数结合 | |

额外问题：

```text
provisional_promotion_trials
```

同时被用作：

- 最少试验次数；
- 最少正确次数；
- 最少证据通过次数。

这三个概念被一个数字绑定，不能分别调整。

## 5. 候选数量和 Workflow 步骤硬上限

| ID | 位置 | 写死值 | 影响 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| A01 | `runtime/workflow_executor.py:251` | 最大 3 | 图片串行执行的 `min(3, max_workflow_attempts)` 覆盖更大的 `workflow_top_k`；冻结视频并行 OR 会执行全部检索 Workflow | 优先取消图片路径的第二层硬 cap，统一由配置决定 | |
| A02 | `growth/workflow_mutator.py:402` | 4+1 | 只保留前 4 个非 MLLM 证据步骤和最后一个 MLLM | 建议改为配置或根据依赖图保留，不应按位置盲截断 | |
| A03 | `growth/workflow_mutator.py:393` | 1 | 没有 MLLM 时只保留第一条 embedding，其他证据步骤全部丢弃 | 很可能可以取消 | |
| A04 | `growth/mutation.py:326` | 3 | 每个 mutation portfolio 最多 3 个 atom | 建议可调；完全取消可能组合爆炸 | |
| A05 | `growth/param_space.py:75` | 3 | `atoms_per_portfolio` 默认再次固定为 3 | 与 A04 合并成一个配置源 | |
| A06 | `growth/param_space.py:142` | 3 | mutation selector 默认只选择 3 个候选 | 已受 C02/C03 控制时，这个默认容易重复约束 | |
| A07 | `growth/skill_consolidator.py:108-109` | 最少 1、默认 12 | active cap 不能设为 0 或 None 来表示关闭 | 建议允许 `None` 关闭，而不是用超大数字模拟 | |
| A08 | `growth/skill_consolidator.py:151` | 至少正确 1 次 | 从未正确的工作流不能 consolidation/active | 属于质量门，通常保留 | |
| A09 | `growth/mutation.py:92-103` | 只重试 1 次 | direction 无合法 atom 时只额外请求一次 LLM | 建议暴露重试次数，或失败后直接跳过 | |
| A10 | `growth/skill_consolidator.py:178-194` | 最多合并 1 条 | 找到第一条可合并 Workflow 后立即 `break` | 虽无显式数字，本质是单次合并限制，建议确认 | |
| A11 | `growth/param_space.py:164` | 最少选择 1 条 | `count` 即使设为 0 或负数也会被 `max(1, count)` 抬到 1 | 若希望用 budget=0 禁用 mutation，应取消该 clamp | |

### A01 的“伪可调”问题

当前调用链：

```text
ExperimentConfig.workflow_top_k
    -> Retriever 返回 top_k 条
    -> CandidateExecutionCoordinator
    -> min(3, max_workflow_attempts)
```

因此在图片探索/图片推理中，把 `workflow_top_k` 改成 10，只会让 Retriever 返回 10 条，但实际仍最多
执行 3 条。冻结视频推理单独返回并执行全部结构合格工作流，不经过这个串行上限。

## 6. 文本、提示词和轨迹截断

这些限制多数不会报错，而是静默截断。

| ID | 位置 | 限制 | 被截断内容 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| T01 | `growth/mutation.py:65` | 8 个空格分词 | 每个 `tool_hint` | 中文不适合按空格分词；建议按字符或 token 可调 | |
| T02 | `growth/mutation.py:71` | 500 字符 | mutation objective | 建议集中配置 | |
| T03 | `growth/mutation.py:75` | 1000 字符 | failure diagnosis | 建议集中配置 | |
| T04 | `growth/mutation.py:135,181` | 末尾 12000 字符 | Workflow 和 observation 上下文 | 会丢最早步骤；建议按结构摘要，不只保留尾部 | |
| T05 | `runtime/workflow_executor.py:67` | 末尾 6000 字符 | 待规范化的 raw answer | 通常可保留，但应命名为配置常量 | |
| T06 | `runtime/workflow_executor.py:392` | 末尾 6000 字符 | 所有候选拒绝原因组成的 ReAct repair context | 候选多时丢掉最早失败原因 | |
| T07 | `runtime/tool_runtime.py:527` | 6000 字符 | `runtime.evidence_text()` | MLLM 看不到更早的工具证据 | |
| T08 | `runtime/tool_runtime.py:629` | 300 字符 | 无法解析时的最终答案 fallback | 长答案会静默裁剪 | |
| T09 | `growth/mutation.py:397-400` | 1000/600/600 | description、exclusions、capability boundary | 建议集中到一个配置对象 | |
| T10 | `growth/mutation.py:412` | 80 字符 | Workflow name | 可保留，但应与 ID/Skill 命名规则区分 | |
| T11 | `growth/skill_consolidator.py:222-234` | 80/1000/600/600 | 合并后的名称和适用性文本 | 与 T09 重复，应共用常量 | |
| T12 | `nodes/mem/spatialskillgrowth/skills/skill_layout.py:18` | 64 字符 | Skill 目录名 | 接近标准 Skill 命名规则，建议保留 | |

删除 T04、T06、T07 可能显著增加 LLM 上下文和费用。更稳妥的方案是：

1. 先统一成有名字的配置；
2. 再决定按字符、token 还是结构化摘要；
3. 允许 `None` 表示不截断；
4. 在轨迹中记录是否发生过截断。

## 7. Mutation 参数菜单和数值先验

### 7.1 离散阈值菜单

位置：

- `growth/param_space.py:24-30`
- `growth/workflow_mutator.py:287-318`
- `growth/workflow_mutator.py:490`

| ID | 工具/字段 | 当前可探索值 | 问题 | 建议 | 你的决定 |
|---|---|---|---|---|---|
| M01 | YOLO threshold | `0.3`, `0.5` | 没有高阈值候选，也不能连续搜索 | 由 Skill/事件定义候选或允许任意数值 | |
| M02 | SAM3 threshold | `0.3`, `0.5`, `0.7` | 固定三档 | 可调菜单或连续区间 | |
| M03 | GroundingDINO box threshold | `0.3`, `0.5` | 固定两档 | 可调菜单 | |
| M04 | GroundingDINO fallback box threshold | `0.35` | 非 box atom 时自动填 0.35 | 集中到工具默认配置 | |
| M05 | GroundingDINO text threshold | `0.25` | 自动生成工作流永远写 0.25 | 应成为 atom 或配置 | |
| M06 | crop/picRelativeCut score | 字符串 `"0.5"` | 自动生成工作流固定过滤 0.5 以下框 | 应继承上游或可调 | |

### 7.2 候选评分常量

| ID | 位置 | 写死值 | 作用 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| M07 | `growth/param_space.py:159` | `0.1` | 每增加一个新工具，selection score 增加 0.1 | 属于算法权重，建议显式配置 | |
| M08 | `growth/param_space.py:207` | `+1/+2` | `(successes+1)/(trials+2)` 拉普拉斯平滑 | 数学先验，通常保留，但应说明可替换 | |
| M09 | `growth/workflow_mutator.py:490` | `0.3/0.5/0.7` | low/medium/high 的统一映射 | 与不同工具真实分布无关，建议按工具拆分 | |

## 8. 视频和图片预处理限制

位置：

- `pipeline/media_processing.py:16-32`
- `pipeline/orchestrator.py:757-760`

| ID | 限制 | 当前值 | 可调情况 | 影响 | 建议 | 你的决定 |
|---|---|---:|---|---|---|---|
| V01 | 默认抽帧率 | 1 fps | 只能通过 `config.extra` 写 Python 调整 | 短促异常可能落在采样间隔中 | 暴露 CLI/env/API | |
| V02 | 单视频最大抽帧数 | 12 | 只能通过 `config.extra` 调整 | 长窗口最多给图片工具 12 帧 | 优先确认是否取消或按时长动态计算 | |
| V03 | 最低抽帧率 | 0.1 fps | 硬编码 | 传入更小值会被抬到 0.1 | 可删除 clamp，改为显式参数验证 | |
| V04 | 最少抽帧数 | 1 | 硬编码 | 不允许配置为 0 来关闭图片工具抽帧 | 可考虑允许 0 表示仅 embedding | |
| V05 | JPEG 质量 | 默认 90 | 构造函数可传，但 Factory 未暴露 | 影响磁盘、速度和小目标清晰度 | 暴露配置 | |
| V06 | JPEG 质量范围 | 1～100 | 协议/库范围 | OpenCV JPEG 质量的合理范围 | 保留 | |
| V07 | 采样点偏移 | 每区间中点 `0.5` | 硬编码 | 不取窗口边缘帧 | 算法选择，建议可替换采样策略 | |
| V08 | 视频末尾避让 | `duration-0.001` 秒 | 硬编码 | 避免精确落在结尾读帧失败 | 低风险，建议保留或命名常量 | |
| V09 | 代表帧 | 列表中间 `len//2` | 硬编码策略 | 首个图片工具前默认只看中间帧 | 可改为显式代表帧策略 | |

注意：支持帧扩散的图片工具可能对全部抽样帧并行执行。所以取消 V02 时，工具调用数和外部服务压力会
线性增长。

## 9. ReAct、Retriever 和并发

| ID | 位置 | 当前值 | 可调情况 | 影响 | 建议 | 你的决定 |
|---|---|---:|---|---|---|---|
| R01 | Agent CLI `--max-react-steps` | 默认 8 | 已可调 | ReAct 最多 8 轮 | 已可调，保留默认即可 | |
| R02 | API `SPATIAL_SKILL_GROWTH_API_MAX_REACT_STEPS` | 默认 8 | 环境变量 | API ReAct 最多 8 轮 | 已可调 | |
| R03 | `ReactSolver` 最小步数 | 1 | 硬 clamp | 不能设 0 来完全跳过 ReAct | 已有 `config.use_react`，最小 1 可保留 | |
| R04 | Retriever top-k 最小值 | 1 | 硬 clamp | 不能用 top_k=0 禁止 Skill 检索 | 可考虑 0 表示只跑 baseline | |
| R05 | 并行图片工具 worker | 默认 4 | 环境变量 | 同一视频多帧并行度 | 已可调 | |
| R06 | worker 最小值 | 1 | 硬 clamp | 不能用 0 表示顺序执行 | 0 的语义不清，建议保留或单独加串行开关 | |

## 10. LLM 调用和生成参数

### 10.1 当前主链路

| ID | 位置 | 当前值 | 可调情况 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| L01 | `config/spatialskillgrowth_config.py:16` | timeout 180 秒 | 环境变量 | 已可调 | |
| L02 | `config/spatialskillgrowth_config.py:18` | temperature 0.7 | 硬编码 | 暴露环境变量；探索和推理可能需要不同值 | |
| L03 | `model/QwenFactory/pureQwenFactory.py:66,91` | 限流重试 3 次 | 硬编码 | 暴露配置或使用统一 retry policy | |
| L04 | `model/QwenFactory/pureQwenFactory.py:77,100` | 每次等待 10 秒 | 硬编码 | 建议指数退避并可调 | |

`MultimodalChatOpenAI` 的重试覆盖会影响 Agent 直接构造的模型，因此 L03/L04 属于主链路。

### 10.2 当前入口未直接使用的 helper 默认值

`get_llm()`、`get_judge_llm()`、`get_multi_llms()` 和 `get_llm_by_url()` 中重复写有：

| ID | 值 | 位置 | 状态 | 建议 | 你的决定 |
|---|---|---|---|---|---|
| L05 | `max_retries=0` | `model/QwenFactory/pureQwenFactory.py:111,130,172,189` | 非主入口 helper | 与自定义重试绑定，集中配置 | |
| L06 | `temperature=0.7` | 同上 | 非主入口 helper | 去重 | |
| L07 | `top_p=0.8` | 同上 | 非主入口 helper | 去重 | |
| L08 | `presence_penalty=1.5` | 同上 | 非主入口 helper | 去重 | |
| L09 | `repetition_penalty=1.0` | 同上 | 非主入口 helper | 去重 | |
| L10 | `top_k=20` | 同上 | 非主入口 helper | 去重 | |

这些值目前没有统一配置，而且在四个函数中重复。

## 11. 工具层超时、阈值和输出限制

| ID | 工具/位置 | 当前限制 | 可调情况 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| U01 | `embeddingTool.py:202` | HTTP timeout 600 秒 | 硬编码 | 暴露统一工具 timeout；不建议完全无超时 | |
| U02 | `groundingDinoTool.py:82` | HTTP timeout 600 秒 | 硬编码 | 同 U01 | |
| U03 | `uniDepthTool.py:89` | HTTP timeout 600 秒 | 硬编码 | 同 U01 | |
| U04 | `pythonSandboxTool.py:110` | 执行 timeout 10 秒 | 硬编码 | 安全限制不建议取消，可调上限 | |
| U05 | `pythonSandboxTool.py:124` | stdout 最多 10000 字符 | 硬编码 | 防止上下文爆炸，建议配置化 | |
| U06 | `pythonSandboxTool.py:80` | 报错只显示前 10 个白名单模块 | 硬编码 | 只是错误展示，可取消 | |
| U07 | `groundingDinoTool.py:25-26` | 默认 0.35/0.25 | 函数参数可调 | 已可由 Workflow 覆盖，保留默认 | |
| U08 | `yoloTool.py:7` | 默认 threshold 0.5 | 函数参数可调 | 已可由 Workflow 覆盖 | |
| U09 | `sam.py:8` | 默认 threshold 0.6 | 函数参数可调 | 已可由 Workflow 覆盖 | |
| U10 | `picCut.py:8,57` | 默认 score `"0.5"` | 函数参数可调 | 已可由 Workflow 覆盖 | |
| U11 | `sam.py:94` | 原始错误响应截断 300 字符 | 硬编码 | 建议与统一错误长度配置合并 | |

额外风险：部分 basicTools 的 `requests.post()` 没有设置 timeout。统一工具超时配置时，应同时处理“固定
600 秒”和“完全没有超时”两类情况。

## 12. SAM3 和图像坐标协议

位置：

- `runtime/tool_contracts.py:30-37`
- `runtime/tool_runtime.py:138-153`
- `runtime/tool_runtime.py:201`
- `runtime/tool_runtime.py:355`

| ID | 约束 | 当前值 | 判断 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| PRT01 | SAM query 英文词数 | 1～3 | 来源于当前模型接口 | 若后端已支持长提示可取消，否则保留 | |
| PRT02 | SAM threshold 范围 | 0～1 | 概率阈值协议 | 保留 | |
| PRT03 | SAM 推荐阈值 | 抽象 0.5；具体 0.6/0.8 | 经验值 | 可从硬 contract 移到文档/配置 | |
| PRT04 | bbox 长度 | 必须 4 | 数据格式 | 保留 | |
| PRT05 | bbox 任一值大于 1 即视为像素坐标 | 边界 1.0 | 启发式判断 | 建议改成显式 bbox_format，避免误判 | |
| PRT06 | 相对坐标范围 | 0～1 | 坐标协议 | 保留 | |

## 13. 输入、验证和命名限制

| ID | 位置 | 当前限制 | 判断 | 建议 | 你的决定 |
|---|---|---|---|---|---|
| I01 | `pipeline/task_router.py:18` | 一次必须正好 1 个媒体 | 当前架构核心输入契约 | 用户已明确“一媒体+一类别”，建议保留 | |
| I02 | `pipeline/evidence_validator.py:42` | 证据门也要求正好 1 个媒体 | 与 I01 重复保证 | 保留或集中到输入模型 | |
| I03 | `skills/human_skill_validation.py:243` | solve 前 3 个参数固定 | Python Skill ABI | 保留 |
| I04 | `skills/skill_layout.py:18` | Skill 名最长 64 | 标准 Skill 命名约束 | 保留 |
| I05 | `growth/skill_consolidator.py:151` | 至少 1 次正确才能激活 | 质量安全门 | 保留 |
| I06 | `pipeline/evidence_validator.py:33-37` | threshold 只检查“是数字” | 注释说 0～1，但代码没有范围检查 | 不是待取消限制；应决定是否补范围验证 | |

## 14. FastAPI 服务限制

| ID | 位置 | 当前值 | 可调情况 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| API01 | 最大上传文件 | 默认 256 MiB | 环境变量 `SPATIAL_SKILL_GROWTH_API_MAX_UPLOAD_BYTES` | 已可调；生产服务不建议取消 | |
| API02 | 上传读取块 | 1 MiB | 硬编码 | 性能参数，建议常量配置化即可 | |
| API03 | 非 embedding 异常覆盖阈值 | 1.0 | 硬编码 | 用户明确要求；若以后要区分模型置信度再改 | |
| API04 | 空文件阈值 | 0 bytes | 输入有效性 | 保留 | |

HTTP 400、500、502 是协议状态码，不属于业务数值限制。

## 15. SQLite 和持久化

| ID | 位置 | 当前限制 | 建议 | 你的决定 |
|---|---|---:|---|---|
| DB01 | `storage/growth_store.py:50` | SQLite connect timeout 30 秒 | 配置化；不建议取消，否则锁竞争可能立即失败或永久等待 | |
| DB02 | task/workflow 哈希后缀 | 8/12 个十六进制字符 | 见下一节；属于碰撞概率折中 | |

## 16. ID 和名称截断

这些数字不限制算法能力，但会影响碰撞概率和可读性。

| ID | 位置 | 当前值 | 用途 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| ID01 | `agents/spatialskillgrowth/online_data.py:141` | SHA1 前 8 位 | 自动 task ID | 数据规模扩大时建议 12～16，或完整 UUID | |
| ID02 | `growth/param_space.py:219` | SHA1 前 12 位 | mutation ID | 通常足够，可保留 | |
| ID03 | `growth/workflow_mutator.py:542` | SHA1 前 12 位 | workflow ID | 通常足够，可保留 | |
| ID04 | `growth/workflow_mutator.py:184` | workflow ID 后 8 位 | Workflow 可读名称 | 只影响显示，可保留 | |
| ID05 | `growth/mutation.py:412` | name 前 80 字符 | LLM 生成名称 | 与 T10 相同，应统一 | |

## 17. 演示、旧工具和非主链路限制

### 17.1 Banner 演示脚本

| ID | 位置 | 数值 | 状态 | 建议 | 你的决定 |
|---|---|---:|---|---|---|
| AUX01 | `scripts/build_banner_demo_dataset.py:15` | 默认 10 条 | `--sample-count` 已可调 | 保留默认 | |
| AUX02 | `scripts/build_banner_demo_dataset.py:18` | JPEG 90 | 演示脚本不可调 | 可复用 V05 配置 | |
| AUX03 | `scripts/run_banner_demo_exploration.py:39` | `min(0.95, 0.55+i*0.01)` | 纯 mock 阈值 | 不影响真实推理，保留或明确删除 demo | |

### 17.2 已不注册的 addedTools

当前工具目录配置为：

```text
SPATIAL_SKILL_GROWTH_TOOLS_DIR = tools/basicTools
```

所以 `tools/addedTools/` 不进入当前异常检测 Runtime。

| ID | 位置 | 数值 | 建议 | 你的决定 |
|---|---|---:|---|---|
| AUX04 | `textInspectorTool.py:51,61` | 文本最多 70000 字符 | 既然工具已去除，可直接删除整个旧工具目录，而非配置数字 | |
| AUX05 | `webSearch.py`, `webVisit.py` | 错误文本最多 200 字符 | 同上 | |

### 17.3 Python Sandbox

Sandbox 属于当前 basicTools，但它的限制主要是安全边界。U04/U05 可以配置化，不建议直接取消。

### 17.4 `agents/spatialskillgrowth/run.sh`

该文件包含：

- `max_model_len=262144`；
- `max-num-seqs=128` 或 `8`；
- `max-num-batched-tokens=16384`；
- GPU memory utilization `0.6` 或 `0.90`；
- tensor parallel size `2`；
- 多个固定端口和 GPU ID。

但它还引用已经删除的 Omni3D Agent 和当前 CLI 不支持的参数，且混入终端输出文本。因此这些数字当前不
属于有效运行配置。建议先决定是否删除或重写整个 `run.sh`，不建议逐个参数配置化。

### 17.5 `mdconvert.py`

`mdconvert.py:578` 使用网络下载 chunk size `512` bytes。它与异常检测主链路无关。如果该工具仍保留，
可以把 chunk size 改成常量；如果项目不再需要 Markdown 转换，可整体移出当前仓库。

## 18. 已经可调、不需要优先处理的数字

| 参数 | 默认值 | 调节方式 |
|---|---:|---|
| 数据集 `--limit` | 0，表示不限 | CLI |
| `--seed` | 3407 | CLI |
| `--max-react-steps` | 8 | CLI |
| LLM timeout | 180 秒 | `SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS` |
| 图片工具并发 | 4 | `SPATIAL_SKILL_GROWTH_PARALLEL_TOOL_WORKERS` |
| API 最大上传 | 256 MiB | `SPATIAL_SKILL_GROWTH_API_MAX_UPLOAD_BYTES` |
| API ReAct 步数 | 8 | `SPATIAL_SKILL_GROWTH_API_MAX_REACT_STEPS` |
| GroundingDINO 0.35/0.25 | Workflow 参数 | `runtime.call` args |
| YOLO 0.5 | Workflow 参数 | `runtime.call` args |
| SAM 0.6 | Workflow 参数 | `runtime.call` args |
| crop score 0.5 | Workflow 参数 | `runtime.call` args |
| Banner demo 样本数 10 | `--sample-count` | CLI |

需要注意：“函数参数可调”和“正式 Agent 入口可调”不是一回事。例如视频 fps/max frames 虽然构造函数能
传，当前 CLI 和 FastAPI 并没有暴露。

## 19. 建议的处理顺序

### 第一批：明显重复或互相冲突

1. A01：删除执行器额外的 `min(3, ...)`；
2. T09/T11：合并重复的名称和适用性文本长度；
3. A04/A05/A06：只保留一个 portfolio/candidate 配置来源；
4. M04/M05/M06：把自动 Workflow 的默认阈值移到工具参数配置；
5. C01～C12：让 `build_experiment_config` 能真正接收参数。

### 第二批：需要你决定是否允许“不限”

1. active cap 12；
2. provisional 每类候选 4；
3. Workflow 执行 3；
4. evidence steps 4；
5. video frames 12；
6. prompt/evidence 字符截断；
7. mutation budget 2/3。

推荐统一约定：

```text
None = 不限制
0    = 禁用该功能
正数 = 明确上限
```

不要继续用 `999999` 表示“不限”。

### 第三批：不应直接取消，只适合配置化

1. HTTP timeout；
2. Sandbox timeout；
3. API 上传大小；
4. 并发 worker；
5. LLM retry 和 backoff；
6. 概率阈值合法范围；
7. Skill 名称长度。

这些限制承担稳定性或安全职责，完全删除可能产生永久阻塞、资源耗尽或不可解析结果。

## 20. 决策记录模板

可以按下面格式给出决定：

```text
P01：取消硬上限，完全跟随 workflow_top_k
P02：改为可配置，默认不限
C04：保留 12
V02：取消 12 帧上限
T04/T06/T07：保留，但统一配置为 20000
U01/U02/U03：统一为环境变量，默认 120 秒
AUX04/AUX05：删除旧工具文件
```

收到决定后，修改时应遵守：

1. 先建立唯一配置来源；
2. 再删除深层函数中的二次 hard cap；
3. 同步 CLI、FastAPI、manifest 和恢复运行的一致性检查；
4. 为 `None/0/正数` 分别写测试；
5. 对取消帧数、候选数和文本长度上限的项目做资源风险测试。
