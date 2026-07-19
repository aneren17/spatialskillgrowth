"""LLM 调用的多模态消息和 JSON 边界。"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Dict, List

from langchain_core.messages import HumanMessage


def invoke_json(llm, prompt: str, image_paths: List[str] | None = None) -> Dict:
    if llm is None:
        raise RuntimeError("This component requires an LLM")
    content = [{"type": "text", "text": prompt}]
    content.extend(image_content(image_paths or []))
    response = llm.invoke([HumanMessage(content=content)])
    return parse_json(getattr(response, "content", response))


def image_content(image_paths: List[str]) -> List[Dict]:
    content = []
    for image_path in image_paths:
        path = Path(str(image_path))
        if not path.is_file():
            continue
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{encoded}",
                "detail": "low",
            },
        })
    return content


def parse_json(value) -> Dict:
    text = str(value or "").strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    parsed = json.loads(match.group(0) if match else text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed
