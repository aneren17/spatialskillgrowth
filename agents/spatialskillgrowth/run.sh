python -m agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent \
    --benchmark omni3d \
    --experiment full \
    --run-id infer_omni3d_501_from_256 \
    --source-experiment full \
    --source-run-id explore_omni3d_256 \
    --source-benchmark omni3d \
    --dataset-dir benchmark/Omni-3d \
    --annotations-file annotations.json \
    --explore-file annotations_explore256.json \
    --images-dir images \
    --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1

python -m agents.spatialskillgrowth.spatialskillgrowth_explore_omni3d_agent \
    --benchmark omni3d \
    --experiment full \
    --run-id explore_omni3d_256 \
    --dataset benchmark/Omni-3d/annotations_explore256.json \
    --img-root benchmark/Omni-3d/images \
    --seed 3407 \
    --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1

python -m agents.spatialskillgrowth.spatialskillgrowth_explore_omni3d_agent \
    --benchmark omni3d \
    --experiment full \
    --run-id explore_omni3d_test_10 \
    --dataset benchmark/Omni-3d/annotations_explore10.json \
    --img-root benchmark/Omni-3d/images \
    --seed 3407 \
    --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1

    
