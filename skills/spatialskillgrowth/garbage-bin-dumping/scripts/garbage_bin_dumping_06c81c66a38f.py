"""Executable SpatialSkillGrowth Skill: garbage_bin_dumping_detector."""

WORKFLOW_ID = 'garbage_bin_dumping_06c81c66a38f'
PROBLEM_CLASS = 'garbage_bin_dumping'
WORKFLOW_GRAPH_SHA256 = '6cf1cc207c110effd498b188321db2e29e0d3ceb484fb7dbe1d93e6fbc80937e'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'garbage_bin_dumping_06c81c66a38f', 'name': 'garbage_bin_dumping_detector', 'problem_class': 'garbage_bin_dumping', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于图像输入，利用多模态大语言模型（MLLM）检测垃圾桶倾倒异常事件。该工作流通过视觉证据分析，判断画面中是否存在垃圾桶被倾倒、侧翻或内容物散落等符合‘垃圾桶倾倒’定义的异常状态。', 'exclusions': '非图像类型的媒体输入（如视频、音频、纯文本）; 需要调用 embeddingTool 进行特征提取的场景; 非‘垃圾桶倾倒’类别的其他异常事件检测; 缺乏清晰视觉证据导致无法判断垃圾桶状态的情况', 'capability_boundary': '{"event_type": "garbage_bin_dumping", "media_type": "image", "evidence_requirement": "必须包含清晰的垃圾桶视觉特征及其倾倒或散落状态证据", "output_format": "binary_classification", "allowed_tools": ["MLLM"], "forbidden_tools": ["embeddingTool"]}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 garbage_bin_dumping 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 garbage_bin_dumping 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 garbage_bin_dumping 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 garbage_bin_dumping 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 garbage_bin_dumping 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
