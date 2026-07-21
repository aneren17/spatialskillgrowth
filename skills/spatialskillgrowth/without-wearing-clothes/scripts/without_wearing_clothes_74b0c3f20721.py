"""Executable SpatialSkillGrowth Skill: without_wearing_clothes_detector."""

WORKFLOW_ID = 'without_wearing_clothes_74b0c3f20721'
PROBLEM_CLASS = 'without_wearing_clothes'
WORKFLOW_GRAPH_SHA256 = '206c12ab3a1a5c1ff7c8a610dcb7e19c9bf7fe0314ad5ca9e7f9ce16c3b78c97'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'without_wearing_clothes_74b0c3f20721', 'name': 'without_wearing_clothes_detector', 'problem_class': 'without_wearing_clothes', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '针对输入图像执行未穿防护服异常检测。工作流首先利用 YOLO 工具以 0.5 的置信度阈值提取视觉特征，随后结合多模态大语言模型分析图像证据，最终判定是否存在未穿防护服行为。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本）; 需要调用 embeddingTool 进行向量检索的场景; 其他类型的异常事件检测（仅限 without_wearing_clothes 类别）', 'capability_boundary': '仅支持静态图像输入；依赖 YOLO 工具（阈值固定为 0.5）进行初步特征提取，并由 MLLM 进行最终语义判断；输出结果严格限制为二元判定（是/否）', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 without_wearing_clothes 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 without_wearing_clothes 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 without_wearing_clothes 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
