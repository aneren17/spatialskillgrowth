"""Executable SpatialSkillGrowth Skill: pipeline_leak_detector."""

WORKFLOW_ID = 'pipeline_leak_d1f7dfcf6135'
PROBLEM_CLASS = 'pipeline_leak'
WORKFLOW_GRAPH_SHA256 = '4e740fd559aadcc07b8dbd5b882117b90ee51e9797909572812fb33d82144529'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'pipeline_leak_d1f7dfcf6135', 'name': 'pipeline_leak_detector', 'problem_class': 'pipeline_leak', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大语言模型（MLLM）对输入图像进行视觉分析，检测是否存在管道泄漏异常。该工作流通过识别图像中的液体喷涌、积水痕迹、管道破损或湿痕等视觉证据，判断是否发生 pipeline_leak 事件。', 'exclusions': '非图像类型的媒体输入（如音频、纯文本）; 需要调用 embeddingTool 进行特征提取的场景; 非管道泄漏类别的异常检测（如火灾、入侵、设备故障等）; 缺乏清晰视觉证据导致无法判断泄漏状态的模糊图像', 'capability_boundary': '{"supported_event_type": "pipeline_leak", "supported_media_type": "image", "required_tools": ["MLLM"], "evidence_requirements": ["必须存在指向管道泄漏的视觉特征（如水流、湿痕、破损点）", "判断依据严格限制于图像内容，不依赖外部上下文或历史数据"]}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 pipeline_leak 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 pipeline_leak 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 pipeline_leak 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 pipeline_leak 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 pipeline_leak 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
