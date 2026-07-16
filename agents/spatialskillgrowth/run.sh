python -m agents.spatialskillgrowth.spatialskillgrowth_explore_omni3d_agent \
    --benchmark anomaly_detection \
    --experiment full \
    --run-id explore_anomaly \
    --dataset benchmark/anomaly/explore.json \
    --img-root benchmark/anomaly/files \
    --seed 3407 \
    --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1

python -m agents.spatialskillgrowth.anomaly_detection_agent \
    --benchmark anomaly_detection \
    --experiment full \
    --run-id infer_anomaly \
    --source-experiment full \
    --source-run-id explore_anomaly \
    --source-benchmark anomaly_detection \
    --dataset benchmark/anomaly/test.json \
    --img-root benchmark/anomaly/files \
    --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1
