"""Executable SpatialSkillGrowth Skill: cross_barrier_detector."""

WORKFLOW_ID = 'cross_barrier_cd9e9a036446'
PROBLEM_CLASS = 'cross_barrier'
WORKFLOW_GRAPH_SHA256 = 'f4ed6d74525c017466b8916e2e0cbed90d1d9a7b3fc7cbb605ab897f6a721daa'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'cross_barrier_cd9e9a036446', 'name': 'cross_barrier_detector', 'problem_class': 'cross_barrier', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '针对静态图像输入，检测是否存在人员或物体翻越、跨越护栏的异常行为。工作流程首先利用 GroundingDINO 以 0.3 的置信度阈值进行开放词汇目标检测，定位潜在的目标与护栏实体；随后结合多模态大语言模型（MLLM）分析视觉证据，判断是否发生跨越动作。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）。; 场景中包含护栏但无人员或物体进行跨越动作的正常通行情况。; 因图像模糊、遮挡严重导致无法清晰识别护栏结构或主体动作的情况。; 涉及其他类型异常事件（如打架、火灾、入侵等）而非翻越护栏的场景。', 'capability_boundary': '{"required_slots": {"event_type": "cross_barrier", "media_type": "image"}, "detection_logic": "基于 GroundingDINO 的开放词汇检测结果（阈值 0.3）与 MLLM 的语义推理联合判定。", "output_format": "二元分类（是/否）", "limitations": "仅适用于静态图像分析，不处理时序动态变化；检测精度依赖于 GroundingDINO 对‘护栏’及‘人体/物体’的识别能力以及 MLLM 对空间关系的理解。"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': "使用低阈值检测 'person', 'barrier', 'fence' 等关键实体，提供结构化位置证据", 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 cross_barrier 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': "使用低阈值检测 'person', 'barrier', 'fence' 等关键实体，提供结构化位置证据", 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 cross_barrier 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 cross_barrier 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
