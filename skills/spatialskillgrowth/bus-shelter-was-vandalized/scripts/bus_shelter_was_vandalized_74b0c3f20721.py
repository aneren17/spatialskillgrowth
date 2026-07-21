"""Executable SpatialSkillGrowth Skill: bus_shelter_vandalism_detector."""

WORKFLOW_ID = 'bus_shelter_was_vandalized_74b0c3f20721'
PROBLEM_CLASS = 'bus_shelter_was_vandalized'
WORKFLOW_GRAPH_SHA256 = '63672a9e1fbcb86608a2728dbb1bbcb839d06f983d0b643c16fb9102e0a6b1a1'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'bus_shelter_was_vandalized_74b0c3f20721', 'name': 'bus_shelter_vandalism_detector', 'problem_class': 'bus_shelter_was_vandalized', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '针对静态图像输入，检测公交站台（候车亭）是否发生物理破坏或人为涂鸦等异常事件。工作流程首先利用目标检测工具（yoloTool）在图像中定位公交站台实体，随后结合多模态大模型（MLLM）分析视觉特征，判断是否存在结构损坏、部件缺失或恶意涂写等破坏性证据。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）。; 图像中未包含公交站台或候车亭实体的场景。; 公交站台存在正常磨损、老化或季节性遮挡，但无明确人为破坏痕迹的情况。; 其他类型的公共设施（如地铁站台、广告牌、路灯）的破坏事件。; 需要调用 embeddingTool 进行语义嵌入处理的场景。', 'capability_boundary': '{"supported_event_type": "bus_shelter_was_vandalized", "required_evidence": ["通过 yoloTool 检测到的公交站台目标框（置信度阈值 >= 0.5）。", "MLLM 基于视觉证据确认的破坏性特征描述（如玻璃破碎、金属变形、涂鸦覆盖等）。"], "tool_dependencies": ["yoloTool: 用于初步定位和存在性验证。", "MLLM: 用于细粒度异常状态判定。"], "output_format": "布尔值（是/否），表示是否检测到破坏事件。"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 bus_shelter_was_vandalized 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 bus_shelter_was_vandalized 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 bus_shelter_was_vandalized 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
