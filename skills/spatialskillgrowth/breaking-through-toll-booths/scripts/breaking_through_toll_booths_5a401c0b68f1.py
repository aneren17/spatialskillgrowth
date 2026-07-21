"""Executable SpatialSkillGrowth Skill: breaking_through_toll_booths_detector."""

WORKFLOW_ID = 'breaking_through_toll_booths_5a401c0b68f1'
PROBLEM_CLASS = 'breaking_through_toll_booths'
WORKFLOW_GRAPH_SHA256 = 'ad1b8945f9a6d3e8af8f6125744f9d548f90739823ff376d9a198b6520dcfd47'
DECLARED_TOOLS = ('paddleOcrTool', 'yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'breaking_through_toll_booths_5a401c0b68f1', 'name': 'breaking_through_toll_booths_detector', 'problem_class': 'breaking_through_toll_booths', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'yoloTool', 'MLLM'], 'description': '基于多模态视觉证据检测图像中是否发生‘闯收费站’异常事件。通过 OCR 提取收费站标识文字、YOLO 检测车辆与收费站结构的空间关系，结合多模态大模型综合判断车辆是否存在强行通过收费站而未正常缴费或通行的行为。', 'exclusions': '非收费站场景（如普通道路、停车场入口、高速公路主线）; 无清晰收费站结构或标识的模糊图像; 车辆正常排队缴费或已通过ETC通道的场景; 非图像模态输入（如视频帧序列、音频、纯文本描述）; 无法识别关键视觉元素（如车辆、收费站栏杆、收费亭）的图像', 'capability_boundary': '{"required_evidence": ["OCR 识别出的收费站相关文字（如‘收费站’、‘缴费’、‘ETC’等）", "YOLO 检测到的车辆与收费站物理结构（如栏杆、收费亭、道闸）的空间位置关系", "多模态模型对车辆行为与收费站状态的综合语义判断"], "detection_scope": "仅限静态图像中单一时间点的闯收费站行为检测", "tool_dependency": "必须依赖 paddleOcrTool 和 yoloTool 的输出作为 MLLM 的输入证据", "output_format": "布尔值（是/否），表示是否检测到闯收费站异常事件"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 breaking_through_toll_booths 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'yolotool_0']}]}


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

    # 依据图像证据判断 breaking_through_toll_booths 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 breaking_through_toll_booths 异常事件。',
        depends_on=['paddleocrtool_0', 'yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
