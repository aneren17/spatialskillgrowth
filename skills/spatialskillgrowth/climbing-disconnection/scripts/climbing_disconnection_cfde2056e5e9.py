"""Executable SpatialSkillGrowth Skill: climbing_disconnection_detector."""

WORKFLOW_ID = 'climbing_disconnection_cfde2056e5e9'
PROBLEM_CLASS = 'climbing_disconnection'
WORKFLOW_GRAPH_SHA256 = 'e7b4ddd8afd9575bf5faa9df7550dc8cf8b8ada3b6e88e1842dbcc34106f2d52'
DECLARED_TOOLS = ('paddleHeadDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'climbing_disconnection_cfde2056e5e9', 'name': 'climbing_disconnection_detector', 'problem_class': 'climbing_disconnection', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'MLLM'], 'description': "针对静态图像输入，检测是否发生'攀爬脱网'异常事件。工作流首先利用 paddleHeadDetTool 定位可见人头，随后结合多模态大模型（MLLM）分析人头与防护网/围栏的空间关系及攀爬姿态，以判定是否存在脱离防护结构的异常行为。", 'exclusions': '非图像类型的媒体输入（如视频流、纯文本描述）。; 图像中未检测到任何可见人头，或人头被严重遮挡导致无法判断其与防护设施的空间关系。; 场景中没有防护网、围栏或类似攀爬防护结构。; 需要实时视频流分析或时序行为追踪的场景（本工作流仅支持单帧静态图像分析）。; 涉及其他类型异常事件（如入侵、跌倒、打架等）的检测需求。', 'capability_boundary': '{"supported_event_type": "climbing_disconnection", "required_evidence": ["可见的人头检测框（由 paddleHeadDetTool 提供）。", "人头与防护设施（如网、围栏）的相对位置及交互状态（由 MLLM 基于图像像素和检测框推理）。", "攀爬姿态或脱离防护结构的视觉特征。"], "input_constraints": {"media_type": "image", "prohibited_tools": ["embeddingTool"]}, "output_format": "布尔值（是/否），表示是否检测到攀爬脱网异常。"}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 climbing_disconnection 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 climbing_disconnection 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 检测可见人头。
    paddleheaddettool_0_result = runtime.call(
        'paddleHeadDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddleHeadDetTool'},
        step_id='paddleheaddettool_0',
        purpose='检测可见人头。',
        depends_on=[],
    )
    runtime.require(paddleheaddettool_0_result, 'paddleheaddettool_0')

    # 依据图像证据判断 climbing_disconnection 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 climbing_disconnection 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 climbing_disconnection 异常事件。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
