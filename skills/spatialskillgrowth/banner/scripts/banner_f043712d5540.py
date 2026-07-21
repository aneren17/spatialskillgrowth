"""Executable SpatialSkillGrowth Skill: banner_anomaly_detector."""

WORKFLOW_ID = 'banner_f043712d5540'
PROBLEM_CLASS = 'banner'
WORKFLOW_GRAPH_SHA256 = 'cfd24a0ae4e197ee7709c2c56f344b5a7529f47b60361097f17e53b11b9f5097'
DECLARED_TOOLS = ('paddleOcrTool', 'groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'banner_f043712d5540', 'name': 'banner_anomaly_detector', 'problem_class': 'banner', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'groundingdino', 'MLLM'], 'description': '检测输入图像中是否存在违规横幅（banner）异常事件。工作流通过 OCR 提取可见文字，并结合开放词汇目标检测定位横幅实体，最终由多模态大模型综合视觉与文本证据进行判定。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 banner 类别的异常检测任务; 不包含可见文字或横幅实体的纯背景图像', 'capability_boundary': '{"required_evidence": ["paddleOcrTool 输出的可见文字内容", "groundingdino 在 0.3 阈值下检测到的横幅实体坐标与类别"], "decision_model": "MLLM", "event_type": "banner", "media_type": "image", "constraint": "仅基于提供的视觉与文本证据判断是否存在违规横幅，不泛化至其他异常类别"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'groundingdino', 'args': {'query': "使用低阈值(0.3)检测'banner'或'ad'区域，以捕获模糊或变形横幅，弥补OCR未检测到文字时的视觉空缺", 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 banner 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 banner 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'groundingdino_0']}]}


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
        {'query': "使用低阈值(0.3)检测'banner'或'ad'区域，以捕获模糊或变形横幅，弥补OCR未检测到文字时的视觉空缺", 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 banner 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 banner 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 banner 异常事件。',
        depends_on=['paddleocrtool_0', 'groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
