"""Executable SpatialSkillGrowth Skill: instrument_operation_detector."""

WORKFLOW_ID = 'instrument_operation_1bd3fad70aa2'
PROBLEM_CLASS = 'instrument_operation'
WORKFLOW_GRAPH_SHA256 = '7f96cc6f06e5aba4400a958ac7c1bdf5693e1a5330a6d02bd82b33086a73ae43'
DECLARED_TOOLS = ('paddleHeadDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'instrument_operation_1bd3fad70aa2', 'name': 'instrument_operation_detector', 'problem_class': 'instrument_operation', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'MLLM'], 'description': '基于视觉证据检测图像中是否存在操作仪器的行为。工作流程首先通过专用工具检测可见人头，随后结合多模态大模型分析图像内容，判断是否发生仪器操作异常。', 'exclusions': '未检测到可见人头的场景; 非图像类型的媒体输入; 需要调用 embedding 工具的场景', 'capability_boundary': '{"required_evidence": ["可见人头检测结果", "仪器操作相关的视觉特征"], "event_type": "instrument_operation", "media_type": "image", "detection_scope": "仅限图像中可见的人头与仪器交互行为，不泛化至无头场景或非仪器类异常"}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 instrument_operation 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 instrument_operation 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0']}]}


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

    # 依据图像证据判断 instrument_operation 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 instrument_operation 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 instrument_operation 异常事件。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
