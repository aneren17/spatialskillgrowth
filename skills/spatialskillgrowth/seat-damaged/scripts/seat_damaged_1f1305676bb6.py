"""Executable SpatialSkillGrowth Skill: seat_damaged_detector."""

WORKFLOW_ID = 'seat_damaged_1f1305676bb6'
PROBLEM_CLASS = 'seat_damaged'
WORKFLOW_GRAPH_SHA256 = '20dc67adb6a62bba6e57501746d2fd21af7b36f7c354d8935832e13e013da43f'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'seat_damaged_1f1305676bb6', 'name': 'seat_damaged_detector', 'problem_class': 'seat_damaged', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大模型（MLLM）对输入图像进行视觉分析，检测是否存在座椅损坏异常。该工作流通过提取图像中的视觉证据，判断座椅结构、表面或功能部件是否出现破损、裂痕、缺失等损坏迹象，最终输出二元判断结果。', 'exclusions': '不适用于非图像类型的媒体输入（如视频、音频或纯文本描述）。; 不处理座椅清洁度问题（如污渍、灰尘），仅关注物理结构或材质的损坏。; 不处理座椅位置偏移、未归位或配置错误等非损坏类异常。; 不处理其他非座椅类物体的损坏检测（如桌子、地板、墙壁等）。; 禁止使用 embeddingTool 进行特征提取，必须依赖 MLLM 的直接视觉推理。', 'capability_boundary': '{"event_type": "seat_damaged", "media_type": "image", "required_evidence": ["座椅物理结构的完整性证据（如裂痕、断裂、变形）", "座椅表面材质的损坏证据（如破损、撕裂、脱落）", "座椅功能部件的缺失或损坏证据（如螺丝松动、部件缺失）"], "output_format": "binary_yes_no", "tool_constraint": "仅使用 MLLM 进行端到端视觉判断，不得引入外部向量检索或嵌入工具"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 seat_damaged 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 seat_damaged 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 seat_damaged 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 seat_damaged 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 seat_damaged 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
