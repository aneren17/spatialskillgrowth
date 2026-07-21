"""Executable SpatialSkillGrowth Skill: fire_detection_workflow."""

WORKFLOW_ID = 'fire_428af33cad44'
PROBLEM_CLASS = 'fire'
WORKFLOW_GRAPH_SHA256 = '64582c7af8ead874d9757757a5bee4e58060a1d9ea72c24b4ee60836d973f820'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fire_428af33cad44', 'name': 'fire_detection_workflow', 'problem_class': 'fire', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测与多模态大语言模型（MLLM）的图像起火异常检测工作流。该流程首先使用 YoloTool 以 0.3 的检测阈值识别图像中的潜在异常目标，随后将检测结果与原始图像输入 MLLM，依据视觉证据判断是否发生“起火”事件。', 'exclusions': '非图像类型的媒体输入（如视频、音频或纯文本）。; 需要调用 embeddingTool 进行特征提取的场景。; 要求对异常事件进行重新分类或泛化到其他火灾子类别（如电气火灾、森林火灾等具体细分）的场景，本工作流仅针对广义的 fire 事件。; 需要输出详细推理过程、置信度分数或除“是/否”以外格式的最终判断。', 'capability_boundary': '{"input_media": "image", "event_type": "fire", "detection_threshold": 0.3, "required_tools": ["yoloTool", "MLLM"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.3}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 检测阈值。', 'args': {}}], 'purpose': '使用 0.3 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 fire 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 fire 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fire 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
