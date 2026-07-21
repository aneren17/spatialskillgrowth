"""Executable SpatialSkillGrowth Skill: egress_blocked_detector."""

WORKFLOW_ID = 'egress_blocked_ca7dd3800fd8'
PROBLEM_CLASS = 'egress_blocked'
WORKFLOW_GRAPH_SHA256 = '1eb7856bec51178e07a5cba91c308e7f9e5390617a9bff285f2fd2d411b1df28'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'egress_blocked_ca7dd3800fd8', 'name': 'egress_blocked_detector', 'problem_class': 'egress_blocked', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '针对图像输入，利用目标检测工具（yoloTool）结合多模态大模型（MLLM）进行视觉证据收集与分析，专门用于判定是否存在安全出口被遮挡或堵塞的异常事件。', 'exclusions': '禁止对图像输入调用 embeddingTool; 不适用于非图像类型的媒体数据; 不处理非 egress_blocked 类别的异常事件; 不进行事件类别的重新分类或改写', 'capability_boundary': '仅支持基于图像视觉证据的 egress_blocked 事件检测，依赖 yoloTool 进行初步特征提取及 MLLM 进行最终逻辑判断，输出结果为二值化的存在性判定。', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 egress_blocked 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 egress_blocked 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 egress_blocked 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 egress_blocked 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 egress_blocked 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
