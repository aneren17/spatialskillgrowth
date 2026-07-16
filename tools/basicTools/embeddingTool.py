import os
import requests
from langchain_core.tools import tool

# 提取并去重后的所有合法 event_type 集合
VALID_EVENT_TYPES = {
    "banner", "fall", "explosion", "fight", "traffic_accident", "pipeline_leak",
    "building_collapse", "cold_flame", "container_dropped", "cross_barrier",
    "ebike_reverse", "egress_blocked", "emergency_lane_occupancy", "equipment_rust",
    "fire_door_unclosed", "firelane_occupied", "flag", "gas_station_smoking",
    "instrument_abnormality", "pedestrian_queue", "platform_yellowline",
    "road_surface_dameged", "run_the_red_light", "screen_doors_clamp_passengers",
    "standing_water", "tank_body_landing", "track_obstacle", "tree_fallen",
    "tube_falls_and_breaks", "bus_shelter_was_vandalized", "climbing_disconnection",
    "doors_and_windows_are_damaged", "garbage_bin_dumping", "guardrail_damaged",
    "seat_damaged", "instrument_operation", "fire", "charger",
    "breaking_through_toll_booths", "billboard_fell", "fire_hydrant_leakage",
    "foreign_objects_on_transmission_lines", "forest_fire", "kitchen_infested_with_rats",
    "license_plate_is_not_standard", "litter_randomly", "lost_manhole_cover",
    "occluded_license_plate", "roadside_booths", "vehicle_illegal_parking",
    "walking_a_dog_without_a_leash", "without_wearing_a_helmet", "without_wearing_a_mask",
    "without_wearing_clothes", "working_at_heights_without_a_safety_harness"
}

@tool
def embeddingTool(file_path: str, event_type: str) -> str:
    """
    Embedding/Detection tool for agent use. The API accepts a local file path (video or image) 
    and an event_type, uploads it to the backend via multipart/form-data, 
    and returns whether an anomaly was detected.

    Args:
        file_path: Local path to the video or image file.
        event_type: The type of event to trigger or detect. MUST be one of the following exactly:
            banner, fall, explosion, fight, traffic_accident, pipeline_leak, building_collapse, 
            cold_flame, container_dropped, cross_barrier, ebike_reverse, egress_blocked, 
            emergency_lane_occupancy, equipment_rust, fire_door_unclosed, firelane_occupied, flag, 
            gas_station_smoking, instrument_abnormality, pedestrian_queue, platform_yellowline, 
            road_surface_dameged, run_the_red_light, screen_doors_clamp_passengers, standing_water, 
            tank_body_landing, track_obstacle, tree_fallen, tube_falls_and_breaks, 
            bus_shelter_was_vandalized, climbing_disconnection, doors_and_windows_are_damaged, 
            garbage_bin_dumping, guardrail_damaged, seat_damaged, instrument_operation, fire, 
            charger, breaking_through_toll_booths, billboard_fell, fire_hydrant_leakage, 
            foreign_objects_on_transmission_lines, forest_fire, kitchen_infested_with_rats, 
            license_plate_is_not_standard, litter_randomly, lost_manhole_cover, occluded_license_plate, 
            roadside_booths, vehicle_illegal_parking, walking_a_dog_without_a_leash, 
            without_wearing_a_helmet, without_wearing_a_mask, without_wearing_clothes, 
            working_at_heights_without_a_safety_harness
    """
    
    # 1. 校验 event_type 是否合法 (拦截幻觉)
    if event_type not in VALID_EVENT_TYPES:
        return (f"Error: Invalid event_type '{event_type}'. "
                f"You must strictly use one of the supported event types. "
                f"Please check the tool description for the valid list and try again.")

    # 2. 校验文件是否存在
    if not isinstance(file_path, str) or not os.path.exists(file_path):
        return f"Error: File does not exist at path: {file_path}"

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
                
                # 判断并返回清晰的结论给 Agent
                if is_anomaly is True:
                    return "Anomaly Detected: True"
                elif is_anomaly is False:
                    return "Anomaly Detected: False"
                else:
                    return f"Error: 'is_anomaly' field missing or invalid in response. Full data: {data_dict}"
            else:
                return f"API returned unexpected status: {resp_json}"
                
    except requests.exceptions.RequestException as e:
        return f"Network error executing embeddingTool: {str(e)}"
    except Exception as e:
        return f"Error executing embeddingTool: {str(e)}"