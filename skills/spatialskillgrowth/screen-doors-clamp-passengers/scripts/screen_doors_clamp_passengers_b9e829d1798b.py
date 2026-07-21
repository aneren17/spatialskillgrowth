"""Executable SpatialSkillGrowth Skill: screen_doors_clamp_passengers_detector."""

WORKFLOW_ID = 'screen_doors_clamp_passengers_b9e829d1798b'
PROBLEM_CLASS = 'screen_doors_clamp_passengers'
WORKFLOW_GRAPH_SHA256 = '444be2030c4e0c415d3d37ff82f95f0e7d6e5781e7bd37226e4cc4caced2f631'
DECLARED_TOOLS = ('paddleHeadDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'screen_doors_clamp_passengers_b9e829d1798b', 'name': 'screen_doors_clamp_passengers_detector', 'problem_class': 'screen_doors_clamp_passengers', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'MLLM'], 'description': '基于图像输入，通过人头检测与多模态大模型推理，判断屏蔽门与乘客之间是否存在夹持异常。', 'exclusions': '非图像类型的媒体输入; 未包含屏蔽门或乘客场景的图像; 需要调用 embeddingTool 的场景; 其他类型的异常事件检测', 'capability_boundary': "仅针对 event_type 为 'screen_doors_clamp_passengers' 且 media_type 为 'image' 的场景，依赖 paddleHeadDetTool 提供的人头检测证据及 MLLM 的视觉推理能力，不泛化至其他异常类别或非图像模态。", 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 screen_doors_clamp_passengers 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 screen_doors_clamp_passengers 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0']}]}


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

    # 依据图像证据判断 screen_doors_clamp_passengers 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 screen_doors_clamp_passengers 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 screen_doors_clamp_passengers 异常事件。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
