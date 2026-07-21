"""Executable SpatialSkillGrowth Skill: instrument_abnormality_detector."""

WORKFLOW_ID = 'instrument_abnormality_07de9c936d38'
PROBLEM_CLASS = 'instrument_abnormality'
WORKFLOW_GRAPH_SHA256 = 'cb7a0bd94037dbe64dc2860a88c300a18dcf48c23b62195bf5c6f267e2e000e7'
DECLARED_TOOLS = ('paddleOcrTool', 'groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'instrument_abnormality_07de9c936d38', 'name': 'instrument_abnormality_detector', 'problem_class': 'instrument_abnormality', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'groundingdino', 'unidepth', 'MLLM'], 'description': '检测输入图像中是否存在仪表异常事件。该工作流通过 OCR 读取仪表可见文字、使用 GroundingDINO 定位仪表组件并估计其深度，最终结合多模态大模型综合视觉证据判断是否发生仪表异常。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非仪表类设备的异常检测; 需要重新分类或改写 event_type 的任务', 'capability_boundary': '{"event_type": "instrument_abnormality", "media_type": "image", "required_evidence": ["OCR 提取的仪表文字信息", "GroundingDINO 检测到的仪表组件位置（阈值 0.3）", "UniDepth 估计的检测目标深度信息"], "output_format": "是/否"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'groundingdino', 'args': {'query': 'instrument_abnormality', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 instrument_abnormality 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'groundingdino_0', 'unidepth_0']}]}


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
        {'query': 'instrument_abnormality', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
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

    # 依据图像证据判断 instrument_abnormality 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 instrument_abnormality 异常事件。',
        depends_on=['paddleocrtool_0', 'groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
