"""Executable SpatialSkillGrowth Skill: fire_hydrant_leakage_detector."""

WORKFLOW_ID = 'fire_hydrant_leakage_0e1ee6980e3f'
PROBLEM_CLASS = 'fire_hydrant_leakage'
WORKFLOW_GRAPH_SHA256 = 'f8c65e6afbd83a8444f83bb56d03df00e68ecf19c4c2081fa53447cdd4ae74b5'
DECLARED_TOOLS = ('groundingdino', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fire_hydrant_leakage_0e1ee6980e3f', 'name': 'fire_hydrant_leakage_detector', 'problem_class': 'fire_hydrant_leakage', 'required_slots': [], 'required_tools': ['groundingdino', 'python_code_sandbox', 'MLLM'], 'description': '基于 GroundingDINO 开放词汇检测与多模态大模型（MLLM）推理的消防栓泄漏异常检测工作流。该工作流通过 0.3 的检测阈值定位消防栓实例，结合 Python 代码沙箱计算结构化视觉证据摘要，最终由 MLLM 依据图像特征判断是否存在泄漏现象。仅适用于静态图像输入，禁止使用嵌入工具。', 'exclusions': '非图像类型的媒体输入（如视频、音频、纯文本）。; 未包含消防栓实体的场景（如普通管道泄漏、非消防水利设施）。; 需要动态时序分析或连续监控的场景。; 依赖 embeddingTool 进行特征提取的流程。; 非 fire_hydrant_leakage 类别的其他异常事件检测任务。', 'capability_boundary': '{"supported_event_type": "fire_hydrant_leakage", "supported_media_type": "image", "detection_method": "GroundingDINO (threshold=0.3) + MLLM reasoning", "evidence_requirement": "必须提供包含消防栓的图像，并生成结构化证据摘要以支持 MLLM 判断。", "output_format": "Binary classification (Yes/No)"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'fire_hydrant_leakage', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fire_hydrant_leakage 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 fire_hydrant_leakage 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'fire_hydrant_leakage', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': runtime.render('import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n')},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 fire_hydrant_leakage 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fire_hydrant_leakage 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fire_hydrant_leakage 异常事件。',
        depends_on=['groundingdino_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
