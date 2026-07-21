"""Executable SpatialSkillGrowth Skill: building_collapse_detector."""

WORKFLOW_ID = 'building_collapse_3f5b81b18890'
PROBLEM_CLASS = 'building_collapse'
WORKFLOW_GRAPH_SHA256 = '5a7ce0be7059ba8fbc5da48571971187f9045bb0e4562cc5ce050ec098db3b4c'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'building_collapse_3f5b81b18890', 'name': 'building_collapse_detector', 'problem_class': 'building_collapse', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测与多模态大语言模型（MLLM）的图像分析工作流，专门用于检测输入图像中是否发生建筑坍塌（building_collapse）异常事件。该工作流通过 YOLO 工具以 0.5 的置信度阈值提取视觉特征，随后由 MLLM 结合图像上下文证据进行最终判定。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行语义嵌入处理的场景; 其他类型的建筑异常事件（如轻微裂缝、火灾、爆炸但未坍塌、正常施工拆除等），本检测器仅针对‘建筑坍塌’这一特定 event_type; YOLO 模型未覆盖或无法有效识别的建筑结构类型', 'capability_boundary': '{"required_event_type": "building_collapse", "supported_media_type": "image", "detection_logic": "首先使用 yolotool_0 进行目标检测（阈值 0.5），随后将检测结果与原始图像输入 mllm_0 进行多模态推理，最终输出二分类判断（是/否）", "object_abstraction_limitation": "由于工具图中未定义可替换的目标物体槽位，本工作流严格限定于检测‘建筑’及其坍塌状态，不可泛化至其他物体（如桥梁、塔楼等，除非其被YOLO预训练类别涵盖且符合建筑定义）"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 building_collapse 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 building_collapse 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 building_collapse 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 building_collapse 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 building_collapse 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
