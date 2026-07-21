"""Executable SpatialSkillGrowth Skill: roadside_booths_detector."""

WORKFLOW_ID = 'roadside_booths_dedd1e22d850'
PROBLEM_CLASS = 'roadside_booths'
WORKFLOW_GRAPH_SHA256 = 'bd8d54bee1f6ec5122bc6061885917de29a8b2dd6737b98aafe272dbb742e479'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'roadside_booths_dedd1e22d850', 'name': 'roadside_booths_detector', 'problem_class': 'roadside_booths', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '基于图像输入，通过OCR提取场景文字信息并结合多模态大模型视觉分析，检测是否存在占道经营（roadside_booths）异常事件。', 'exclusions': '非图像类型的媒体输入; 需要调用embeddingTool的场景; 其他非roadside_booths类别的异常事件检测', 'capability_boundary': '{"required_evidence": ["通过paddleOcrTool获取的可见文字证据", "通过MLLM对图像内容进行的视觉分析证据"], "event_type": "roadside_booths", "media_type": "image", "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 roadside_booths 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


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

    # 依据图像证据判断 roadside_booths 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 roadside_booths 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
