"""Executable SpatialSkillGrowth Skill: cold_flame_detector."""

WORKFLOW_ID = 'cold_flame_8525e5d8e629'
PROBLEM_CLASS = 'cold_flame'
WORKFLOW_GRAPH_SHA256 = '5349db350246ec6369ec33349d70dad50f646f37d426c4ee93c177798757f1bf'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'cold_flame_8525e5d8e629', 'name': 'cold_flame_detector', 'problem_class': 'cold_flame', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '基于视觉证据检测图像中是否存在冷焰火（cold_flame）异常事件。工作流首先使用 GroundingDINO 以 0.3 的开放词汇检测阈值定位潜在目标，随后利用多模态大语言模型（MLLM）结合图像上下文进行最终判定。该流程专用于静态图像输入，旨在通过可复用的视觉证据链确认冷焰火的存在与否。', 'exclusions': '非图像类型的媒体输入（如视频、音频或纯文本）; 需要调用 embeddingTool 的场景; 其他类型的火焰或燃烧事件（非冷焰火类别）; 动态实时流媒体检测场景', 'capability_boundary': '{"input_media": "image", "event_type": "cold_flame", "detection_threshold": 0.3, "evidence_chain": ["groundingdino_object_localization", "mllm_contextual_reasoning"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': '使用低阈值检测潜在的光源、烟雾或异常物体，为MLLM提供具体的空间位置证据', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 cold_flame 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 cold_flame 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': '使用低阈值检测潜在的光源、烟雾或异常物体，为MLLM提供具体的空间位置证据', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 cold_flame 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 cold_flame 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 cold_flame 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
