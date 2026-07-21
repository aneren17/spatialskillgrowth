"""Executable SpatialSkillGrowth Skill: screen_doors_clamp_passengers_detector."""

WORKFLOW_ID = 'screen_doors_clamp_passengers_2ebebd3e0e79'
PROBLEM_CLASS = 'screen_doors_clamp_passengers'
WORKFLOW_GRAPH_SHA256 = '259628352a1770ade711ff5a0c05a0532e923fd5ff65e640a8361f18ef42acae'
DECLARED_TOOLS = ('paddleHeadDetTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'screen_doors_clamp_passengers_2ebebd3e0e79', 'name': 'screen_doors_clamp_passengers_detector', 'problem_class': 'screen_doors_clamp_passengers', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'unidepth', 'MLLM'], 'description': '基于图像输入，通过人头检测、深度估计及多模态大模型推理，检测地铁站台屏蔽门是否发生夹人异常事件。', 'exclusions': '非图像类型的媒体输入; 非屏蔽门夹人（screen_doors_clamp_passengers）类别的其他异常事件; 需要调用 embeddingTool 的场景', 'capability_boundary': '{"required_inputs": ["包含站台屏蔽门区域的图像"], "evidence_requirements": ["必须检测到可见人头（paddleHeadDetTool）", "必须获取检测目标的深度信息（unidepth）", "必须通过多模态模型（MLLM）综合视觉证据进行最终判断"], "output_format": "布尔值（是/否）"}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.paddleheaddettool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['paddleheaddettool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 screen_doors_clamp_passengers 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 screen_doors_clamp_passengers 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0', 'unidepth_0']}]}


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

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(paddleheaddettool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 screen_doors_clamp_passengers 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 screen_doors_clamp_passengers 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 screen_doors_clamp_passengers 异常事件。',
        depends_on=['paddleheaddettool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
