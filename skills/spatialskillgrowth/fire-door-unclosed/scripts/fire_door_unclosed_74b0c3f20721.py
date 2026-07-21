"""Executable SpatialSkillGrowth Skill: fire_door_unclosed_detector."""

WORKFLOW_ID = 'fire_door_unclosed_74b0c3f20721'
PROBLEM_CLASS = 'fire_door_unclosed'
WORKFLOW_GRAPH_SHA256 = '53cb1c7e222090428f7f56a9ec35022f9d96f2f0b5111b869bde1d6051113c95'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fire_door_unclosed_74b0c3f20721', 'name': 'fire_door_unclosed_detector', 'problem_class': 'fire_door_unclosed', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测与多模态大语言模型（MLLM）的视觉分析工作流，用于检测输入图像中是否存在消防门未关闭的异常状态。该工作流首先利用 YOLO 工具以 0.5 的置信度阈值提取关键视觉特征，随后由 MLLM 结合图像证据进行语义推理，最终判定是否发生消防门未关闭事件。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行特征嵌入的场景; 非 fire_door_unclosed 类别的其他异常事件检测任务; 缺乏清晰消防门视觉特征或图像质量过低导致无法识别门体状态的场景', 'capability_boundary': '仅支持对静态图像进行 fire_door_unclosed 异常事件的二元判定（是/否）。检测逻辑严格依赖于 YOLO 工具在 0.5 阈值下的检测结果以及 MLLM 对视觉证据的语义分析，不包含对门体机械故障原因的分析或对其他类型安全门（如普通防火门、逃生门）的通用未关闭检测能力，除非明确指定为 fire_door_unclosed 事件类型。', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 fire_door_unclosed 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 fire_door_unclosed 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fire_door_unclosed 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
