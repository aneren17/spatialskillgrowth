"""SpatialSkillGrowth 的全部中文 LLM 提示词。业务模块不得内嵌提示词正文。"""

ANOMALY_INPUT_QUESTION_PROMPT = """请检测输入{media_name}中是否发生“{event_name}”异常事件。
该类别已经由调用方确定，精确 event_type 为 `{event_type}`，不要重新分类或改写类别。
相关中文名称：{aliases}。必须调用 embeddingTool 获取异常判断和判定阈值。
最终判断只使用“是”或“否”，同时在结构化结果中保留 event_type、is_anomaly 和 threshold。"""

FREE_REACT_SYSTEM_PROMPT = """你是一个多模态异常事件检测智能体。请使用可用工具判断当前视频或
图像中是否发生问题指定的异常事件。优先调用 embeddingTool，并使用当前任务类别对应的精确英文
event_type；不得翻译、改写或编造 event_type。仅构造足以回答问题的最短证据链，不要重复无信息量
的调用；工具失败时才改用相关工具补充证据。证据充分后，只返回 JSON：
{"answer": "用户要求的最终答案"}。不要在 answer 字段之外输出推理过程或单位。"""

REACT_FINALIZATION_PROMPT = """工具调用预算已经耗尽，不要再请求工具。请只依据当前对话中的
问题和已有观察，立即给出证据支持度最高的最终答案。只返回 JSON：
{"answer": "用户要求的最终答案"}。"""

WORKFLOW_REJECTION_CONTEXT_PROMPT = (
    "工作流 {workflow_id} 未通过证据验收：{reason}。候选答案：{answer}。"
)
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
WORKFLOW_DEFAULT_ANSWER_PROMPT = (
    "请使用明确的{role}证据回答问题，只输出最终答案：$question"
)
WORKFLOW_COMBINED_SEMANTIC_ANSWER_PROMPT = (
    "请针对 {problem_class} 分析{scope}，并同时遵守以下推理和证据要求：{requirements}。"
    "如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question"
)
WORKFLOW_FINAL_ANSWER_PROMPT = (
    "请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。"
    "\n证据：\n$evidence\n问题：$question"
)

PROBLEM_CLASSIFIER_PROMPT = """请把当前多模态异常检测问题严格分类到给定的一个异常事件类别。
类别名是 embeddingTool 接口使用的精确英文 event_type。判断问题要求检测的异常事件，不要根据
无关物体、答案选项、措辞重叠或类别频率分类。只能返回 JSON：
{{"problem_class": "给定列表中的精确类别名", "reason": "简短中文理由"}}。

异常事件类别：
{class_definitions}

问题：
{question}
"""

SLOT_EXTRACTION_PROMPT = """请从多模态异常检测问题和输入图像中抽取可复用的运行时槽位，
不要回答问题。event_type 必须等于当前 problem_class，保持精确英文 ID，不能翻译或改写。
target_a、target_b 是简短指代表达；由于 SAM3 和 GroundingDINO 的接口限制，sam_query_a、
sam_query_b 必须分别是 1～3 个英文单词的物体标签，不能使用句子。只返回包含以下键的 JSON：
event_type、target_a、target_b、sam_query_a、sam_query_b、reference_frame、reference_entity、
reference_value、reference_unit、measurement_dimension、operation。

当前异常事件类别：{problem_class}
问题：{question}
"""

FLAT_WORKFLOW_RETRIEVAL_PROMPT = """请为当前多模态异常检测任务排序可复用工作流。所有候选都已
通过结构兼容性检查，并属于同一个异常事件类别。请综合判断自然语言适用范围、排除条件、能力边界、
当前图像所需证据、运行时槽位、工具图和已验证历史。不要根据工作流 ID、措辞重叠、物体名称重叠
或答案选项选择。优先考虑事件类别匹配度、证据适用性和验证历史；复杂度和工具成本只能用于同等
候选之间的决胜。最多返回 {top_k} 个精确工作流 ID；如果没有候选可能有效，必须拒绝全部。

只返回 JSON：
{{
  "action": "select|reject_all",
  "ranked_workflow_ids": ["精确工作流 ID"],
  "reason": "简短的中文语义与证据理由"
}}

异常事件类别：{problem_class}
答案类型：{answer_type}
运行时槽位：{slot_bindings}
问题：{question}
候选工作流：{candidates}
"""

WORKFLOW_TREE_RETRIEVAL_PROMPT = """请沿给定工作流树选择一个可复用工作流。把当前异常事件语义
和运行时槽位与每条路线的自然语言适用范围进行匹配。子节点是父节点的细化版本，只有当前任务确实
需要该细化时才选择子节点。不要根据答案选项中的共有词或不透明的工作流 ID 选择；历史次数只能
用于语义同样适用的路线之间决胜。

只返回 JSON：
{{
  "workflow_path": ["根工作流 ID", "可选的子工作流 ID"],
  "workflow_id": "最终工作流 ID",
  "reason": "简短中文适用性理由"
}}

异常事件类别：{problem_class}
运行时槽位：{slot_bindings}
问题：{question}
工作流树：{workflow_tree}
"""

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
四个键的 JSON，字段内容使用中文，name 可以保留安全的英文标识。

异常事件类别：{problem_class}
问题：{question}
运行时槽位：{slot_bindings}
变异模式：{mutation_mode}
工具图：{tool_graph}
"""

APPLICABILITY_COMPATIBILITY_PROMPT = """请判断两个结构兼容的异常检测工作流是否具有相同的
可复用自然语言适用范围。结构已经单独检查；这里只判断语义适用范围、排除条件和能力边界。不能把
关键词或物体名称重叠当作兼容证据。只有一条泛化路线能够诚实表示两者时才允许合并。

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

SEMANTIC_EVIDENCE_VALIDATION_PROMPT = """请判断工作流观察是否提供了足够的任务相关证据来接受
候选答案。不能只根据语言流畅度或格式判断。对于异常事件检测，必须确认 embeddingTool 使用了
与当前 problem class 完全一致的 event_type，并成功返回异常判断；如果使用其他视觉工具补证，
还要确认观察确实涉及所要求的事件、对象或行为。任何关键工具失败都不能被忽略。数值类答案必须
展示相关检测实例、测量值、参考值或中间操作数，并给出能够支持精确数值的推导；只有裸数值或
MLLM 无可观察来源的断言不足以通过。只返回 JSON：
{{"accepted": true|false, "reason": "简短中文证据理由"}}。

异常事件类别：{problem_class}
答案类型：{answer_type}
问题：{question}
候选答案：{answer}
观察：{observations}
"""
