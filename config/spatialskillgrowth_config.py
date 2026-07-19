"""Engineering configuration for the independent SpatialSkillGrowth architecture."""

import os

from dotenv import load_dotenv

load_dotenv()

SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE = os.getenv(
    "SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE", "Qwen3.6-27B-FP8"
)
SPATIAL_SKILL_GROWTH_BASE_URL = os.getenv(
    "SPATIAL_SKILL_GROWTH_BASE_URL", "http://127.0.0.1:8861/v1"
)
SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS = int(
    os.getenv("SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS", "180")
)
SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE = 0.7
SPATIAL_SKILL_GROWTH_PARALLEL_TOOL_WORKERS = int(
    os.getenv("SPATIAL_SKILL_GROWTH_PARALLEL_TOOL_WORKERS", "4")
)

SPATIAL_SKILL_GROWTH_TOOLS_DIR = "tools/basicTools"
