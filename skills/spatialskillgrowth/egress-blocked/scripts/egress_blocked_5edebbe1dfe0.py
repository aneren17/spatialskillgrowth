"""Executable SpatialSkillGrowth Skill: egress_blocked_detector."""

WORKFLOW_ID = 'egress_blocked_5edebbe1dfe0'
PROBLEM_CLASS = 'egress_blocked'
WORKFLOW_GRAPH_SHA256 = '3fb97de22daa1ff8a4ba0856cba18e87a00d4a19cfccd979a68ca4b2367bdb44'
DECLARED_TOOLS = ('groundingdino', 'paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'egress_blocked_5edebbe1dfe0', 'name': 'egress_blocked_detector', 'problem_class': 'egress_blocked', 'required_slots': [], 'required_tools': ['groundingdino', 'paddleOcrTool', 'MLLM'], 'description': '针对图像输入，通过开放词汇目标检测与安全出口标识文字识别，验证是否存在安全出口被物理遮挡或堵塞的异常事件。', 'exclusions': '非图像类型的媒体输入; 非安全出口遮挡类的其他异常事件; 需要调用 embedding 工具的特征提取任务', 'capability_boundary': '{"required_evidence": ["通过 groundingdino 检测到的潜在遮挡物体及其位置关系", "通过 paddleocr 识别的安全出口相关标识文字"], "tool_constraints": ["必须使用 groundingdino 进行视觉目标定位", "必须使用 paddleocr 进行文字信息提取", "禁止使用 embeddingTool"], "decision_logic": "基于视觉证据综合判断是否发生 egress_blocked 事件，输出二值结果"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': '使用低阈值检测潜在遮挡物（如箱子、家具），确保不遗漏低置信度目标', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 egress_blocked 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 egress_blocked 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'paddleocrtool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': '使用低阈值检测潜在遮挡物（如箱子、家具），确保不遗漏低置信度目标', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 读取可见文字。
    paddleocrtool_0_result = runtime.call(
        'paddleOcrTool',
        {'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='paddleocrtool_0',
        purpose='读取可见文字。',
        depends_on=[],
    )
    runtime.require(paddleocrtool_0_result, 'paddleocrtool_0')

    # 依据图像证据判断 egress_blocked 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 egress_blocked 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 egress_blocked 异常事件。',
        depends_on=['groundingdino_0', 'paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
