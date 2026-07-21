"""Executable SpatialSkillGrowth Skill: doors_and_windows_are_damaged_detector."""

WORKFLOW_ID = 'doors_and_windows_are_damaged_f16c7937be91'
PROBLEM_CLASS = 'doors_and_windows_are_damaged'
WORKFLOW_GRAPH_SHA256 = 'e0ce51e6a6527d7b54f5bc67438a2b10d313b220aaef80a45f3dec06d206e73c'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'doors_and_windows_are_damaged_f16c7937be91', 'name': 'doors_and_windows_are_damaged_detector', 'problem_class': 'doors_and_windows_are_damaged', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '检测输入图像中是否存在门窗破损或损坏的异常事件。该工作流利用多模态大语言模型（MLLM）直接分析图像视觉特征，识别门或窗结构上的物理损伤证据，如破碎、裂痕、缺失部件或严重变形。', 'exclusions': '非图像类型的媒体输入（如纯文本、音频或视频流）; 未包含门或窗主体的图像场景; 门窗外观正常但功能异常（如无法开关）且无可见物理破损的情况; 需要调用 embeddingTool 进行语义嵌入处理的场景; 需要区分具体破损原因（如人为破坏 vs 自然灾害）的细粒度归因任务', 'capability_boundary': '{"supported_event_type": "doors_and_windows_are_damaged", "supported_media_type": "image", "required_evidence": "视觉可见的物理结构损坏（如玻璃破碎、框架断裂、铰链脱落等）", "tool_constraints": "仅使用 MLLM 进行视觉推理，禁止使用 embeddingTool", "output_format": "布尔值（是/否）"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 doors_and_windows_are_damaged 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 doors_and_windows_are_damaged 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 doors_and_windows_are_damaged 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 doors_and_windows_are_damaged 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 doors_and_windows_are_damaged 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
