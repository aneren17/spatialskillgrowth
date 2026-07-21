"""Executable SpatialSkillGrowth Skill: guardrail_damaged_detector."""

WORKFLOW_ID = 'guardrail_damaged_74b0c3f20721'
PROBLEM_CLASS = 'guardrail_damaged'
WORKFLOW_GRAPH_SHA256 = 'da9951d5b72ad358bae53f704b096d936c679d2dacf5755d0ddd675ed96d2c31'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'guardrail_damaged_74b0c3f20721', 'name': 'guardrail_damaged_detector', 'problem_class': 'guardrail_damaged', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测（阈值 0.5）与多模态大模型推理，针对输入图像中护栏结构完整性进行异常检测，识别护栏损坏事件。', 'exclusions': '非图像类型的媒体输入; 护栏缺失但非损坏的情况; 其他非护栏类基础设施的损坏事件; 需要调用 embeddingTool 的场景', 'capability_boundary': '{"event_type": "guardrail_damaged", "media_type": "image", "required_evidence": ["yoloTool 检测结果（阈值 0.5）", "MLLM 基于视觉证据的损坏判定"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 guardrail_damaged 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 guardrail_damaged 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 guardrail_damaged 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
