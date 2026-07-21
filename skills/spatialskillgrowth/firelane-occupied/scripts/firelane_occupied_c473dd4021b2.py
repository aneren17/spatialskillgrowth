"""Executable SpatialSkillGrowth Skill: firelane_occupied_detector."""

WORKFLOW_ID = 'firelane_occupied_c473dd4021b2'
PROBLEM_CLASS = 'firelane_occupied'
WORKFLOW_GRAPH_SHA256 = 'f788f9eabbba3e37a5d517ee3e24813f230bbeffbe6b4172caad34282900c9cb'
DECLARED_TOOLS = ('paddleOcrTool', 'paddlePedriderDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'firelane_occupied_c473dd4021b2', 'name': 'firelane_occupied_detector', 'problem_class': 'firelane_occupied', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'paddlePedriderDetTool', 'MLLM'], 'description': '检测输入图像中是否存在占用消防通道的异常事件。该工作流通过光学字符识别提取场景文字信息，结合交通参与者检测识别潜在障碍物，最终由多模态大模型综合视觉与文本证据，判断消防通道是否被违规占用。', 'exclusions': '非图像类型的媒体输入; 需要调用 embedding 工具的场景; 非 firelane_occupied 类别的异常检测任务; 无法通过 paddleOcrTool 或 paddlePedriderDetTool 获取有效证据的模糊或遮挡严重图像', 'capability_boundary': '{"required_tools": ["paddleOcrTool", "paddlePedriderDetTool", "MLLM"], "evidence_requirements": ["可见文字信息（如消防通道标识、禁止停车标志等）", "交通参与者或障碍物检测结果（如车辆、行人、堆放物等）"], "output_format": "binary_yes_no", "event_type_constraint": "firelane_occupied"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'paddlePedriderDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddlePedriderDetTool'}, 'param_atoms': [{'tool_name': 'paddlePedriderDetTool', 'axis': 'target', 'value': 'traffic_subject', 'kind': 'fixed', 'description': '检测交通参与者。', 'args': {}}], 'purpose': '检测交通参与者。', 'step_id': 'paddlepedriderdettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 firelane_occupied 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 firelane_occupied 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'paddlepedriderdettool_0']}]}


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

    # 检测交通参与者。
    paddlepedriderdettool_0_result = runtime.call(
        'paddlePedriderDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddlePedriderDetTool'},
        step_id='paddlepedriderdettool_0',
        purpose='检测交通参与者。',
        depends_on=[],
    )
    runtime.require(paddlepedriderdettool_0_result, 'paddlepedriderdettool_0')

    # 依据图像证据判断 firelane_occupied 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 firelane_occupied 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 firelane_occupied 异常事件。',
        depends_on=['paddleocrtool_0', 'paddlepedriderdettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
