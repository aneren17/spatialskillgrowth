"""异常检测 Agent 的公开入口，保留旧 Omni3D 模块作为兼容实现。"""

from agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent import (
    SpatialSkillGrowthAnomalyDetectionAgent,
    build_parser,
    main,
)


__all__ = [
    "SpatialSkillGrowthAnomalyDetectionAgent",
    "build_parser",
    "main",
]


if __name__ == "__main__":
    main()
