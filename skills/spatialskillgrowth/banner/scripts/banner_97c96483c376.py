"""Executable SpatialSkillGrowth Skill: banner_detection_workflow."""

WORKFLOW_ID = 'banner_97c96483c376'
PROBLEM_CLASS = 'banner'
WORKFLOW_GRAPH_SHA256 = '8af1749f1deeea9ef3617337deeaab2ae7ed13ddcede27cb63106fa19cae2530'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'banner_97c96483c376', 'name': 'banner_detection_workflow', 'problem_class': 'banner', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '针对图像输入，通过 OCR 提取可见文字并结合多模态模型视觉分析，检测是否存在违规横幅（banner）异常事件。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 banner 类别的异常检测任务; 无法通过 OCR 或多模态视觉证据判断的场景', 'capability_boundary': '{"required_inputs": ["image"], "event_type": "banner", "evidence_sources": ["paddleOcrTool 提取的文本内容", "MLLM 基于图像视觉特征的判断"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 banner 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 banner 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


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

    # 依据图像证据判断 banner 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 banner 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 banner 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
