"""Executable SpatialSkillGrowth Skill: lost_manhole_cover_detector."""

WORKFLOW_ID = 'lost_manhole_cover_428af33cad44'
PROBLEM_CLASS = 'lost_manhole_cover'
WORKFLOW_GRAPH_SHA256 = 'e135f7dabff76d63f9f12e136fab3d78e007d2067a6ed6d85aa3c94a0cbf5792'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'lost_manhole_cover_428af33cad44', 'name': 'lost_manhole_cover_detector', 'problem_class': 'lost_manhole_cover', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测（阈值 0.3）与多模态大模型推理，检测输入图像中是否存在井盖丢失或井盖未盖好的异常事件。', 'exclusions': '非图像类型的媒体输入; 非井盖丢失或未盖好类别的其他异常事件; 需要调用 embeddingTool 的场景', 'capability_boundary': '{"required_slots": ["event_type", "media_type"], "fixed_event_type": "lost_manhole_cover", "fixed_media_type": "image", "detection_logic": "使用 yolotool 进行初步目标定位，随后通过 MLLM 结合视觉证据进行最终异常判定", "output_format": "布尔值（是/否）"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.3}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 检测阈值。', 'args': {}}], 'purpose': '使用 0.3 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 lost_manhole_cover 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.3},
        step_id='yolotool_0',
        purpose='使用 0.3 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 依据图像证据判断 lost_manhole_cover 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 lost_manhole_cover 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
