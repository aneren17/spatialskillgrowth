"""Executable SpatialSkillGrowth Skill: egress_blocked_detector."""

WORKFLOW_ID = 'egress_blocked_bf89f2a3b4ab'
PROBLEM_CLASS = 'egress_blocked'
WORKFLOW_GRAPH_SHA256 = '13307f1ce97e158227b603fb37245d0e1fef03eaef18e0bcdf53446b1a93574b'
DECLARED_TOOLS = ('paddleOcrTool', 'groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'egress_blocked_bf89f2a3b4ab', 'name': 'egress_blocked_detector', 'problem_class': 'egress_blocked', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'groundingdino', 'unidepth', 'MLLM'], 'description': '基于多模态视觉证据检测安全出口遮挡异常。工作流首先通过 OCR 识别场景中的文字标识以确认出口属性，利用开放词汇检测模型（阈值 0.3）定位潜在遮挡物，并结合深度估计分析空间关系，最终由多模态大模型综合判断是否存在 egress_blocked 事件。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 egress_blocked 类别的异常检测任务; 无法通过视觉证据直接判断遮挡关系的抽象场景', 'capability_boundary': '仅支持针对 egress_blocked 事件的图像检测，依赖 paddleOcrTool、groundingdino、unidepth 和 MLLM 的协同推理，不泛化至其他异常类别或非视觉模态。', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'groundingdino', 'args': {'query': 'egress_blocked', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 egress_blocked 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 egress_blocked 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'groundingdino_0', 'unidepth_0']}]}


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

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'egress_blocked', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(groundingdino_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 egress_blocked 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 egress_blocked 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 egress_blocked 异常事件。',
        depends_on=['paddleocrtool_0', 'groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
