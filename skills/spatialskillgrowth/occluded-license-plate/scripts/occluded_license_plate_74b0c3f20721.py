"""Executable SpatialSkillGrowth Skill: occluded_license_plate_detector."""

WORKFLOW_ID = 'occluded_license_plate_74b0c3f20721'
PROBLEM_CLASS = 'occluded_license_plate'
WORKFLOW_GRAPH_SHA256 = '9b0dcecc20e1a8d7081445349092c189ccbbc1b83c9f01a772b28bb0e2f78a91'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'occluded_license_plate_74b0c3f20721', 'name': 'occluded_license_plate_detector', 'problem_class': 'occluded_license_plate', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '检测输入图像中是否存在车牌遮挡异常事件。工作流程首先使用 YOLO 工具（检测阈值 0.5）进行目标检测，随后结合多模态大语言模型（MLLM）依据视觉证据判断是否发生车牌遮挡。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非车牌遮挡类的其他异常事件检测', 'capability_boundary': '{"event_type": "occluded_license_plate", "media_type": "image", "required_tools": ["yoloTool", "MLLM"], "constraints": ["禁止使用 embeddingTool", "必须保留 yolotool_0 的 0.5 检测阈值设置", "仅针对车牌遮挡这一特定事件类型进行判断"]}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 occluded_license_plate 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.5 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.5},
        step_id='yolotool_0',
        purpose='使用 0.5 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 依据图像证据判断 occluded_license_plate 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 occluded_license_plate 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
