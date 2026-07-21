"""Executable SpatialSkillGrowth Skill: instrument_abnormality_detector."""

WORKFLOW_ID = 'instrument_abnormality_dedd1e22d850'
PROBLEM_CLASS = 'instrument_abnormality'
WORKFLOW_GRAPH_SHA256 = '3f53c3dcd7b8424a5656d6691223873b34419cac2680687a60ae6aaacdaf4b97'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'instrument_abnormality_dedd1e22d850', 'name': 'instrument_abnormality_detector', 'problem_class': 'instrument_abnormality', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '基于图像输入，通过 OCR 提取可见文字并结合多模态大模型视觉分析，检测仪表是否存在异常状态。该工作流严格依赖图像中的视觉证据（如指针位置、数字读数、警示标识等）进行判断，适用于各类静态仪表盘的异常识别场景。', 'exclusions': '非图像类型的媒体输入（如纯文本、音频、视频流）; 无法通过 OCR 或视觉模型直接观测到的仪表内部机械故障或隐性电路故障; 需要实时动态序列分析才能判定的瞬态异常（本工作流仅处理单帧静态图像）; 图像中仪表区域被严重遮挡、模糊或完全不可见的情况', 'capability_boundary': '{"event_type": "instrument_abnormality", "media_type": "image", "required_evidence": ["OCR 提取的仪表盘面文字信息", "多模态模型对仪表指针、刻度、指示灯及整体状态的视觉解析"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 instrument_abnormality 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


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

    # 依据图像证据判断 instrument_abnormality 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 instrument_abnormality 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
