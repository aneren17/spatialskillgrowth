"""Executable SpatialSkillGrowth Skill: breaking_through_toll_booths_detector."""

WORKFLOW_ID = 'breaking_through_toll_booths_e7ed2b3b5674'
PROBLEM_CLASS = 'breaking_through_toll_booths'
WORKFLOW_GRAPH_SHA256 = '4f84ce66a5d80f7eeb9bb4b7d3be87f077f4b33aa9ef6b900ab184f26e1ecf88'
DECLARED_TOOLS = ('paddleOcrTool', 'yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'breaking_through_toll_booths_e7ed2b3b5674', 'name': 'breaking_through_toll_booths_detector', 'problem_class': 'breaking_through_toll_booths', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'yoloTool', 'unidepth', 'MLLM'], 'description': '检测输入图像中是否发生车辆或物体强行通过收费站（Toll Booth）的异常事件。该工作流通过 OCR 识别收费站标识文字、YOLO 检测车辆及收费站结构、UniDepth 估计空间深度关系，结合多模态大模型综合判断是否存在‘闯收费站’行为。', 'exclusions': '非收费站场景（如普通路口、停车场入口、无收费设施的通道）; 车辆正常排队缴费或通过已抬起栏杆的收费站; 图像中未包含收费站关键结构（栏杆、亭子、标识牌）或车辆; 模糊、遮挡严重导致无法识别收费站状态或车辆行为的图像; 非图像媒体类型（本工作流仅支持 image 类型输入）', 'capability_boundary': '{"required_evidence": ["OCR 识别到收费站相关文字（如‘收费’、‘ETC’、‘收费站’等）", "YOLO 检测到车辆与收费站栏杆/亭子的空间共存", "UniDepth 估计显示车辆处于栏杆未抬起或应停止区域", "多模态模型确认车辆行为符合‘强行通过’而非正常通行"], "tool_constraints": ["paddleOcrTool 必须成功读取收费站标识文字", "yoloTool 必须使用 0.5 检测阈值定位车辆与收费站结构", "unidepth 必须基于 yoloTool 输出估计目标深度", "MLLM 必须综合上述三项证据进行最终判断"], "event_type_lock": "breaking_through_toll_booths", "media_type_lock": "image"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 breaking_through_toll_booths 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'yolotool_0', 'unidepth_0']}]}


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

    # 使用 0.5 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.5},
        step_id='yolotool_0',
        purpose='使用 0.5 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(yolotool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['yolotool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 breaking_through_toll_booths 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 breaking_through_toll_booths 异常事件。',
        depends_on=['paddleocrtool_0', 'yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
