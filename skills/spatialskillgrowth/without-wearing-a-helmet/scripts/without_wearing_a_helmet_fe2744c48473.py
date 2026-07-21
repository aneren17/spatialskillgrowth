"""Executable SpatialSkillGrowth Skill: without_wearing_a_helmet."""

WORKFLOW_ID = 'without_wearing_a_helmet_fe2744c48473'
PROBLEM_CLASS = 'without_wearing_a_helmet'
WORKFLOW_GRAPH_SHA256 = 'c782ee4cf62afd9d5ce0d5a1dd1de4d1303045011edc1a240bdbd8270a136241'
DECLARED_TOOLS = ('paddleHeadDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'without_wearing_a_helmet_fe2744c48473', 'name': 'without_wearing_a_helmet', 'problem_class': 'without_wearing_a_helmet', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'MLLM'], 'description': '基于图像输入，利用人头检测工具定位可见人头，并结合多模态大语言模型分析视觉证据，以判断场景中是否存在人员未佩戴安全帽的异常行为。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）。; 图像中完全未检测到可见人头或人头区域被严重遮挡导致无法辨识头部特征的情况。; 需要调用 embeddingTool 进行语义嵌入的场景（本工作流禁止使用）。; 涉及其他类型安全违规（如未穿反光衣、未系安全带等）的检测任务。', 'capability_boundary': '{"event_type": "without_wearing_a_helmet", "media_type": "image", "required_evidence": ["通过 paddleHeadDetTool 获取的可见人头边界框及置信度。", "通过 MLLM 基于人头区域图像内容生成的关于是否佩戴安全帽的视觉分析结论。"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 without_wearing_a_helmet 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 without_wearing_a_helmet 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 检测可见人头。
    paddleheaddettool_0_result = runtime.call(
        'paddleHeadDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddleHeadDetTool'},
        step_id='paddleheaddettool_0',
        purpose='检测可见人头。',
        depends_on=[],
    )
    runtime.require(paddleheaddettool_0_result, 'paddleheaddettool_0')

    # 依据图像证据判断 without_wearing_a_helmet 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 without_wearing_a_helmet 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 without_wearing_a_helmet 异常事件。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
