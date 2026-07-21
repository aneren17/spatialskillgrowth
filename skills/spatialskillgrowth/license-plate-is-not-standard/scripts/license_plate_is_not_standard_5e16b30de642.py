"""Executable SpatialSkillGrowth Skill: license_plate_is_not_standard_detector."""

WORKFLOW_ID = 'license_plate_is_not_standard_5e16b30de642'
PROBLEM_CLASS = 'license_plate_is_not_standard'
WORKFLOW_GRAPH_SHA256 = 'cda12b99008c7a0f26c1a97aa722c0d8cd163aba64ec36bb7f808fa4072a1b8d'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'license_plate_is_not_standard_5e16b30de642', 'name': 'license_plate_is_not_standard_detector', 'problem_class': 'license_plate_is_not_standard', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '针对图像输入，通过光学字符识别提取可见文字，并结合多模态大模型视觉分析，检测车牌是否存在不规范异常事件。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 license_plate_is_not_standard 类别的其他异常检测任务', 'capability_boundary': '严格限定于 event_type 为 license_plate_is_not_standard 且 media_type 为 image 的场景，依赖 paddleOcrTool 提取文字证据及 MLLM 进行最终视觉判定。', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 license_plate_is_not_standard 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。; 给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 license_plate_is_not_standard 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 读取可见文字。
    paddleocrtool_0_result = runtime.call(
        'paddleOcrTool',
        {'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='paddleocrtool_0',
        purpose='读取可见文字。',
        depends_on=[],
    )
    runtime.require(paddleocrtool_0_result, 'paddleocrtool_0')

    # 依据图像证据判断 license_plate_is_not_standard 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 license_plate_is_not_standard 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。; 给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 license_plate_is_not_standard 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
