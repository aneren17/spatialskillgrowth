"""SpatialSkillGrowth 的全部中文 LLM 提示词。业务模块不得内嵌提示词正文。"""

ANOMALY_INPUT_QUESTION_PROMPT = """请检测输入{media_name}中是否发生“{event_name}”异常事件。
该类别已经由调用方确定，精确 event_type 为 `{event_type}`，不要重新分类或改写类别。
相关中文名称：{aliases}。{media_tool_instruction}
最终判断只使用“是”或“否”。"""

ANOMALY_MEDIA_TOOL_INSTRUCTIONS = {
    "image": (
        "图片输入禁止调用 embeddingTool；请使用图像工具和多模态模型收集可复用视觉证据。"
    ),
    "video": (
        "embeddingTool 只能接收原始视频；图像工具只能处理按时间抽取的视频帧。"
    ),
}

FREE_REACT_SYSTEM_PROMPT = """你是一个多模态异常事件检测智能体。请使用可用工具判断当前视频或
图像中是否发生问题指定的异常事件。embeddingTool 只允许接收原始视频，禁止向它传入图片或视频
抽样帧；图片任务应使用图像工具和 MLLM，视频任务可同时使用原视频 embeddingTool 与抽样帧工具。
event_type 必须使用当前任务类别对应的精确英文 ID，不得翻译、改写或编造。仅构造足以回答问题的
最短证据链，不要重复无信息量的调用；工具失败时才改用相关工具补充证据。证据充分后，只返回 JSON：
{"answer": "用户要求的最终答案"}。不要在 answer 字段之外输出推理过程或单位。"""

REACT_FINALIZATION_PROMPT = """工具调用预算已经耗尽，不要再请求工具。请只依据当前对话中的
问题和已有观察，立即给出证据支持度最高的最终答案。只返回 JSON：
{"answer": "用户要求的最终答案"}。"""

WORKFLOW_REJECTION_CONTEXT_PROMPT = (
    "工作流 {workflow_id} 未通过证据验收：{reason}。候选答案：{answer}。"
)
SKILL_GUIDED_WORKFLOW_RETRIEVAL_PROMPT = """请从同一异常事件类别的候选工作流中选择最适合当前
输入的工作流。`SKILL.md` 是这些工作流的简明使用说明书，必须先阅读 Skill 作用、工作流选择规则
和可选工作流，再结合当前视频抽帧或图像证据进行排序。候选工作流 JSON 是机器契约，用来核对
详细适用范围、工具链、运行时槽位和历史指标。

不要仅根据工作流名称、ID、工具数量或文字重叠选择。历史准确率、证据通过率和调用成本只用于
适用性相近时的排序。如果没有候选满足说明书和当前证据条件，返回 reject_all。

只返回 JSON：
{{
  "action": "select|reject_all",
  "ranked_workflow_ids": ["最多 {top_k} 个精确工作流 ID"],
  "reason": "简短中文理由"
}}

异常事件类别：{event_type}
运行时槽位：{slot_bindings}
问题：{question}

同类别 SKILL.md：
{skill_guidance}

候选工作流：
{candidates}
"""
REACT_ATTACHMENT_PROMPT = "\n附件路径：\n{paths}"
REACT_VIDEO_ATTACHMENT_PROMPT = """
原始检测窗口视频（只传给支持视频的 embeddingTool）：{media_path}
按时间顺序抽取的图像帧（只传给图像工具）：
{frame_paths}
不要把原始视频传给仅支持图像的工具，也不要把抽样帧代替原视频传给 embeddingTool。"""

FINAL_ANSWER_NORMALIZATION_PROMPT = """请把视觉智能体的原始回答规范成问题要求的精确格式。
这一步只做格式整理：保留原回答表达的结论，不要重新解题，不要添加原回答未断言的信息，也不要
使用图像。只返回 JSON：{{"answer": "规范化后的答案"}}。

期望答案类型：{answer_type}
问题：{question}
原始回答：{raw_answer}
"""

WORKFLOW_NORMALIZED_QUERY_PROMPT = (
    "请依据明确的异常检测证据回答，只输出最终答案：$question"
)
WORKFLOW_COMBINED_SEMANTIC_ANSWER_PROMPT = (
    "请针对 {problem_class} 分析{scope}，并同时遵守以下推理和证据要求：{requirements}。"
    "如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question"
)
WORKFLOW_FINAL_ANSWER_PROMPT = (
    "请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。"
    "\n证据：\n$evidence\n问题：$question"
)

SUCCESS_ENHANCEMENT_DIRECTION_PROMPT = """请为已经正确回答探索任务的异常检测工作流规划增强
方向。目标是在不破坏已验证路线的前提下，提高鲁棒性、补充证据或形成有价值的新能力边界。你不会
接收真实答案，也不得推测真实答案。只能从给定 ParamType 原子 ID 中选择方向，不得编造工具、
位置、分数或最终答案。

只返回 JSON：
{{
  "objective": "简短增强目标",
  "preferred_atom_ids": ["精确原子 ID"],
  "avoid_atom_ids": ["精确原子 ID"],
  "tool_hints": {{"精确工具名": "简短运行时目标提示"}},
  "diagnosis": "该方向如何补充已有成功证据"
}}

异常事件类别：{problem_class}
问题：{question}
运行时槽位：{slot_bindings}
成功工作流和观察：{workflow_context}
允许的 ParamType 原子：{param_atoms}
"""

FAILURE_REPAIR_DIRECTION_PROMPT = """请诊断异常检测工作流在当前探索样例上失败的原因，并规划
能够修复缺失证据的变异。真实答案只能用于诊断：严禁把真实答案、其变换值或能反推出答案的线索
写入工具提示、工作流参数、适用范围、名称或任何可复用资产。只能从给定 ParamType 原子 ID 中
选择方向，不得编造工具、位置或分数。

只返回 JSON：
{{
  "objective": "简短修复目标",
  "preferred_atom_ids": ["精确原子 ID"],
  "avoid_atom_ids": ["精确原子 ID"],
  "tool_hints": {{"精确工具名": "简短运行时目标提示"}},
  "diagnosis": "证据层面的失败诊断"
}}

异常事件类别：{problem_class}
问题：{question}
错误预测：{prediction}
仅供诊断的真实答案：{groundtruth}
运行时槽位：{slot_bindings}
失败工作流和观察：{workflow_context}
允许的 ParamType 原子：{param_atoms}
"""

MUTATION_DIRECTION_RETRY_PROMPT = """上一次变异方向没有选中任何合法 ParamType 原子。请从
给定列表中选择一至三个最能实现当前目标和证据诊断的精确 ID，不得编造或改写 ID。只返回完整
方向 JSON，键必须是 objective、preferred_atom_ids、avoid_atom_ids、tool_hints、diagnosis。

变异模式：{mode}
上一次方向：{direction}
允许的工具：{allowed_tools}
允许的 ParamType 原子 ID：{allowed_atom_ids}
"""

GROUNDTRUTH_SAFE_DIRECTION_PROMPT = """请把失败修复方向改写成可复用、与具体答案无关的证据
诊断。真实答案只能用于理解失败原因。必须删除所有精确、部分、舍入、变换或间接泄露答案的线索，
同时保留原修复意图；只能使用给定的 ParamType 原子 ID 和工具名。只返回完整方向 JSON，键必须
是 objective、preferred_atom_ids、avoid_atom_ids、tool_hints、diagnosis。不要返回真实答案，
也不要解释改写过程。

仅供脱敏的真实答案：{groundtruth}
候选方向：{direction}
允许的工具：{allowed_tools}
允许的 ParamType 原子 ID：{allowed_atom_ids}
"""

APPLICABILITY_GENERALIZATION_PROMPT = """请为一个已由真实答案验证的异常检测工作流编写可复用
的中文适用范围。应泛化事件检测操作和证据条件，但不得包含任务 ID、最终答案、具体场景故事、
benchmark 切分、奖励或实现历史。保持给定工具图不变，不要把某个具体异常事件扩大成全部异常
类别。必须保留当前 event_type 和所需证据边界。只有工具图包含可替换目标的运行时槽位时，才能
抽象物体名称；没有对应槽位时，必须在适用范围或排除条件中明确检测器限制。必需槽位由工具图引用
自动推导，不能从自然语言臆测。只返回包含 name、description、exclusions、capability_boundary
四个键的 JSON，字段内容使用中文，name 可以保留安全的英文标识。这些字段只写入
`references/workflows/*.json` 的机器契约，不得生成、改写或覆盖人工维护的 `SKILL.md` 与
`scripts/*.py`。

异常事件类别：{problem_class}
问题：{question}
运行时槽位：{slot_bindings}
变异模式：{mutation_mode}
工具图：{tool_graph}
"""

APPLICABILITY_COMPATIBILITY_PROMPT = """请判断两个结构兼容的异常检测工作流是否具有相同的
可复用自然语言适用范围。结构已经单独检查；这里只判断语义适用范围、排除条件和能力边界。不能把
关键词或物体名称重叠当作兼容证据。人工与自动工作流按相同语义标准处理。只有一条泛化路线能够
诚实表示两者时才允许合并，且合并只更新 references 中的工作流契约，不覆盖人工脚本和 SKILL.md。

只返回 JSON：
{{
  "action": "merge|separate",
  "reason": "简短中文语义理由",
  "generalized_name": "合并后的名称",
  "generalized_description": "合并后的中文适用范围",
  "generalized_exclusions": "合并后的中文排除条件",
  "generalized_capability_boundary": "合并后的中文能力边界"
}}

左侧工作流：{left}
右侧工作流：{right}
"""
