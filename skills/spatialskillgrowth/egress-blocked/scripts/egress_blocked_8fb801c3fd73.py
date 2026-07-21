"""Executable SpatialSkillGrowth Skill: egress_blocked_detector."""

WORKFLOW_ID = 'egress_blocked_8fb801c3fd73'
PROBLEM_CLASS = 'egress_blocked'
WORKFLOW_GRAPH_SHA256 = 'e73907831e70f1b67443744818665c79dbd2766da3919f4e3c548587f2ba4b3b'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'egress_blocked_8fb801c3fd73', 'name': 'egress_blocked_detector', 'problem_class': 'egress_blocked', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '针对静态图像输入，通过光学字符识别（OCR）提取场景中的可见文字信息，并结合多模态大语言模型（MLLM）进行视觉语义分析，以检测是否存在‘安全出口遮挡’（egress_blocked）异常事件。该工作流专注于验证安全出口通道是否被物理障碍物堵塞或标识被遮挡，确保证据链包含视觉特征与文本信息的综合判断。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本日志）。; 需要动态时序分析的场景，本工作流仅处理单帧静态图像。; 其他类型的异常事件（如火灾、入侵、设备故障等），本检测器仅针对 egress_blocked 类别。; 无法通过 OCR 或视觉模型识别的极端低质量、模糊或完全黑暗图像。', 'capability_boundary': '{"required_inputs": ["image"], "required_evidence": ["paddleOcrTool 提取的可见文字内容", "MLLM 基于图像视觉特征及 OCR 结果的综合判断"], "tool_constraints": ["禁止调用 embeddingTool。", "必须使用 paddleOcrTool 进行文字读取。", "必须使用 MLLM 进行最终异常判定。"], "event_type": "egress_blocked"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 egress_blocked 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 egress_blocked 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


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

    # 依据图像证据判断 egress_blocked 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 egress_blocked 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 egress_blocked 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
