import os

import requests
from langchain_core.tools import tool


VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}

# event_type 是后端接口的稳定标识，不能翻译或改写。三份映射分别保留各前端的原始显示名称。
DASHBOARD_EVENT_LABELS = {
    "banner": "违规横幅检测",
    "fall": "人员摔倒",
    "explosion": "爆炸检测",
    "fight": "打架斗殴",
    "traffic_accident": "交通事故",
    "pipeline_leak": "管道泄漏",
    "building_collapse": "建筑坍塌",
    "cold_flame": "冷焰火检测",
    "container_dropped": "集装箱掉落",
    "cross_barrier": "翻越护栏",
    "ebike_reverse": "非机动车逆行",
    "egress_blocked": "安全出口遮挡",
    "emergency_lane_occupancy": "占用应急车道",
    "equipment_rust": "设备生锈",
    "fire_door_unclosed": "消防门未关闭",
    "firelane_occupied": "占用消防通道",
    "flag": "旗帜检测",
    "gas_station_smoking": "加油站抽烟",
    "instrument_abnormality": "仪表异常",
    "pedestrian_queue": "行人排队聚集",
    "platform_yellowline": "越过站台黄线",
    "road_surface_dameged": "路面破损",
    "run_the_red_light": "闯红灯",
    "screen_doors_clamp_passengers": "屏蔽门夹人",
    "standing_water": "积水检测",
    "tank_body_landing": "罐体落地",
    "track_obstacle": "轨道异物",
    "tree_fallen": "树木倒伏",
    "tube_falls_and_breaks": "试管掉落破碎",
    "bus_shelter_was_vandalized": "公交站台破坏",
    "climbing_disconnection": "攀爬脱网",
    "doors_and_windows_are_damaged": "门窗破损",
    "garbage_bin_dumping": "垃圾桶倾倒",
    "guardrail_damaged": "护栏损坏",
    "seat_damaged": "座椅损坏",
    "instrument_operation": "是否操作仪器",
    "fire": "起火",
    "charger": "充电器未归位",
}

RAG_EVENT_LABELS = {
    "banner": "横幅异常",
    "fire_door_unclosed": "消防门未关闭",
    "fall": "跌倒",
    "fight": "打架",
    "explosion": "爆炸",
    "emergency_lane_occupancy": "应急车道占用",
    "traffic_accident": "交通事故",
    "breaking_through_toll_booths": "闯收费站",
    "building_collapse": "建筑倒塌",
    "bus_shelter_was_vandalized": "公交候车亭损坏",
    "climbing_disconnection": "攀爬脱离",
    "cold_flame": "冷焰",
    "container_dropped": "集装箱坠落",
    "cross_barrier": "跨越护栏",
    "doors_and_windows_are_damaged": "门窗损坏",
    "ebike_reverse": "电动车逆行",
    "egress_blocked": "出口堵塞",
    "equipment_rust": "设备生锈",
    "firelane_occupied": "消防通道占用",
    "flag": "旗帜异常",
    "garbage_bin_dumping": "垃圾桶倾倒",
    "gas_station_smoking": "加油站吸烟",
    "guardrail_damaged": "护栏损坏",
    "instrument_abnormality": "仪表异常",
    "pedestrian_queue": "行人排队",
    "pipeline_leak": "管道泄漏",
    "platform_yellowline": "站台黄线",
    "road_surface_dameged": "路面损坏",
    "run_the_red_light": "闯红灯",
    "screen_doors_clamp_passengers": "屏蔽门夹人",
    "seat_damaged": "座位损坏",
    "standing_water": "积水",
    "tank_body_landing": "罐体着陆",
    "track_obstacle": "轨道障碍物",
    "tree_fallen": "树木倒塌",
    "tube_falls_and_breaks": "管道坠落破裂",
    "billboard_fell": "广告牌倒塌",
    "fire_hydrant_leakage": "消防栓泄漏",
    "foreign_objects_on_transmission_lines": "输电线路异物",
    "forest_fire": "森林火灾",
    "kitchen_infested_with_rats": "厨房出现老鼠",
    "license_plate_is_not_standard": "车牌不规范",
    "litter_randomly": "随地乱扔垃圾",
    "lost_manhole_cover": "井盖丢失或井盖没盖好",
    "occluded_license_plate": "车牌遮挡",
    "roadside_booths": "占道经营",
    "vehicle_illegal_parking": "车辆违停",
    "walking_a_dog_without_a_leash": "遛狗未牵绳",
    "without_wearing_a_helmet": "未戴安全帽",
    "without_wearing_a_mask": "未戴口罩",
    "without_wearing_clothes": "未穿防护服",
    "working_at_heights_without_a_safety_harness": "高空作业未系安全带",
}

STREAM_EVENT_LABELS = {
    "banner": "横幅异常",
    "fire_door_unclosed": "消防门未关闭",
    "fall": "跌倒",
    "fight": "打架",
    "explosion": "爆炸",
    "traffic_accident": "交通事故",
    "emergency_lane_occupancy": "应急车道占用",
    "building_collapse": "建筑倒塌",
    "forest_fire": "森林火灾",
}

EVENT_LABEL_SOURCES = {
    "dashboard": DASHBOARD_EVENT_LABELS,
    "rag": RAG_EVENT_LABELS,
    "stream": STREAM_EVENT_LABELS,
}
VALID_EVENT_TYPES = frozenset(
    event_type
    for labels in EVENT_LABEL_SOURCES.values()
    for event_type in labels
)
EVENT_TYPE_SOURCE_LABELS = {
    event_type: {
        source: labels[event_type]
        for source, labels in EVENT_LABEL_SOURCES.items()
        if event_type in labels
    }
    for event_type in sorted(VALID_EVENT_TYPES)
}
EVENT_TYPE_ALIASES = {
    event_type: list(dict.fromkeys(source_labels.values()))
    for event_type, source_labels in EVENT_TYPE_SOURCE_LABELS.items()
}
# 大屏端名称优先作为标准标题；只在 RAG/实时端出现的类别使用其已有名称。
EVENT_TYPE_LABELS = {
    event_type: (
        DASHBOARD_EVENT_LABELS.get(event_type)
        or RAG_EVENT_LABELS.get(event_type)
        or STREAM_EVENT_LABELS[event_type]
    )
    for event_type in sorted(VALID_EVENT_TYPES)
}

def _embedding_tool_description() -> str:
    lines = [
        "视频异常事件检测工具。输入本地原始视频路径以及精确的英文 event_type，",
        "将文件上传到后端检测服务，并返回该异常事件是否发生及对应的判定阈值。",
        "该工具不支持图片或视频抽样帧，图片输入必须使用其他视觉工具。",
        "event_type 不能翻译、改写或自行创造。支持的类别及中文显示名称如下：",
    ]
    for event_type in sorted(VALID_EVENT_TYPES):
        aliases = "；".join(EVENT_TYPE_ALIASES[event_type])
        lines.append(f"- {event_type}：{aliases}")
    lines.extend([
        "参数 file_path：本地原始视频文件路径。",
        "参数 event_type：上面列表中的精确英文类别 ID。",
        "返回：检测到该异常事件时返回‘是’（并附带阈值），否则返回‘否’（并附带阈值）。",
    ])
    return "\n".join(lines)

@tool
def embeddingTool(file_path: str, event_type: str) -> str:
    """
    视频异常事件检测工具。输入本地原始视频路径以及异常事件类别，工具会将文件上传到
    后端检测服务，并返回该类别的异常事件是否发生以及检测阈值。

    event_type 必须严格使用工具描述列出的英文类别 ID，不能翻译、改写或自行创造。

    Args:
        file_path: 本地原始视频文件路径。
        event_type: 要检测的异常事件类别，必须是工具描述中的精确英文 ID。
    """
    
    # 1. 校验 event_type 是否合法 (拦截幻觉)
    if event_type not in VALID_EVENT_TYPES:
        return (f"Error: Invalid event_type '{event_type}'. "
                f"必须严格使用工具描述中列出的 event_type，请检查后重试。")

    # 2. 校验文件是否存在
    if not isinstance(file_path, str) or not os.path.exists(file_path):
        return f"Error: File does not exist at path: {file_path}"
    suffix = os.path.splitext(file_path)[1].lower()
    if suffix not in VIDEO_SUFFIXES:
        return "Error: embeddingTool only supports original video files."

    url = "http://172.16.0.91:8080/api/detect" 
    
    # 构造 form-data
    data = {
        "event_type": event_type
    }

    try:
        # 使用 with 语句确保文件正确关闭
        with open(file_path, "rb") as f:
            # requests 的 files 参数格式: {"field_name": (filename, file_object)}
            files = {
                "file": (os.path.basename(file_path), f)
            }
            
            # 发送 multipart/form-data POST 请求
            response = requests.post(url, files=files, data=data, timeout=600)
            response.raise_for_status()
            
            resp_json = response.json()
            
            # 校验外层状态
            if resp_json.get("status") == "success":
                # 提取 data 字典
                data_dict = resp_json.get("data", {})

                # 直接获取 is_anomaly 字段
                is_anomaly = data_dict.get("is_anomaly")

                # 安全提取 metrics 中的 threshold 字段
                metrics = data_dict.get("metrics") or {}
                if not isinstance(metrics, dict):
                    metrics = {}
                threshold = metrics.get("threshold")

                # 格式化阈值输出文本
                threshold_info = f" (判定阈值: {threshold})" if threshold is not None else ""

                # 判断并返回清晰的结论给 Agent
                if is_anomaly is True:
                    return f"是{threshold_info}"
                elif is_anomaly is False:
                    return f"否{threshold_info}"
                else:
                    return f"Error: 'is_anomaly' field missing or invalid in response. Full data: {data_dict}"
            else:
                return f"API returned unexpected status: {resp_json}"
                
    except requests.exceptions.RequestException as e:
        return f"Network error executing embeddingTool: {str(e)}"
    except Exception as e:
        return f"Error executing embeddingTool: {str(e)}"

embeddingTool.description = _embedding_tool_description()
