"""Executable SpatialSkillGrowth Skill: walking_a_dog_without_a_leash_detector."""

WORKFLOW_ID = 'walking_a_dog_without_a_leash_7bf76f25c40f'
PROBLEM_CLASS = 'walking_a_dog_without_a_leash'
WORKFLOW_GRAPH_SHA256 = '69ad0fc8e24016cb6cc05ee765ff83e434bc1551d8863ca3262cd7c0dd1440a0'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'walking_a_dog_without_a_leash_7bf76f25c40f', 'name': 'walking_a_dog_without_a_leash_detector', 'problem_class': 'walking_a_dog_without_a_leash', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测与多模态大模型（MLLM）的图像分析工作流，专门用于检测输入图像中是否存在‘遛狗未牵绳’的异常行为。该流程首先通过 YOLO 工具以 0.5 的置信度阈值识别图像中的关键主体（如人、狗、牵引绳等），随后利用 MLLM 结合视觉证据进行语义推理，判断是否满足‘人在遛狗’且‘未使用牵引绳’的条件。', 'exclusions': '非图像类型的媒体输入（如视频、音频或纯文本）; 需要调用 embeddingTool 进行向量检索或嵌入生成的任务; 涉及其他类型异常事件（如打架、盗窃、火灾等）的检测需求; 需要修改或覆盖人工维护的 SKILL.md 与 scripts/*.py 文件的场景; 图像中主体模糊、遮挡严重导致无法明确判断人与狗关系及牵引绳状态的情况', 'capability_boundary': '{"input_constraints": "仅接受静态图像输入，禁止使用 embeddingTool", "detection_scope": "严格限定于 event_type 为 \'walking_a_dog_without_a_leash\' 的场景，不泛化至其他遛狗相关行为（如牵绳遛狗、狗绳断裂等）或其他异常类别", "evidence_requirements": "必须包含 YOLO 检测到的实体边界框及 MLLM 基于视觉证据的逻辑判断结果", "output_format": "最终判断结果仅限‘是’或‘否’"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 walking_a_dog_without_a_leash 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 walking_a_dog_without_a_leash 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 walking_a_dog_without_a_leash 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 walking_a_dog_without_a_leash 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 walking_a_dog_without_a_leash 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
