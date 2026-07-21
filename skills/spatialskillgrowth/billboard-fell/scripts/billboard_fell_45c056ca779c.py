"""Executable SpatialSkillGrowth Skill: billboard_fell_detector."""

WORKFLOW_ID = 'billboard_fell_45c056ca779c'
PROBLEM_CLASS = 'billboard_fell'
WORKFLOW_GRAPH_SHA256 = '8442f04fb874ed5d9b22b96273bc02b511a4150eb0495921cc53515461bd090e'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'billboard_fell_45c056ca779c', 'name': 'billboard_fell_detector', 'problem_class': 'billboard_fell', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '基于视觉证据检测图像中是否发生广告牌倒塌异常事件。工作流通过开放词汇检测定位广告牌结构，结合深度估计分析其空间姿态与完整性，最终由多模态模型判定是否发生倒塌。', 'exclusions': '仅适用于静态图像输入，不支持视频流或实时动态监测; 仅检测已确认的 billboard_fell 事件类型，不泛化至其他结构倒塌或物体坠落场景; 检测目标严格限定为广告牌（billboard），不适用于其他大型户外标识或建筑结构; 依赖 groundingdino 检测到的广告牌实例，若检测失败则无法执行后续深度与状态分析', 'capability_boundary': '{"required_tools": ["groundingdino", "unidepth", "MLLM"], "input_constraints": {"media_type": "image", "detection_threshold": 0.3}, "evidence_requirements": ["必须通过 groundingdino 定位广告牌实体", "必须通过 unidepth 获取检测目标的深度信息以辅助姿态判断", "最终判定需由 MLLM 综合视觉特征与深度证据得出"], "output_format": "binary (是/否)"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': "使用中等阈值检测'billboard', 'debris', 'structure'等关键实体，提供定位证据", 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 billboard_fell 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': "使用中等阈值检测'billboard', 'debris', 'structure'等关键实体，提供定位证据", 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(groundingdino_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 billboard_fell 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 billboard_fell 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
