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


docker rm -f v_qwen36 || true
docker run --gpus all --name v_qwen36 \
    -v /usb:/usb \
    -e CUDA_VISIBLE_DEVICES=0,1 \
    -d \
    --net=host \
    --restart=always \
    --entrypoint /usr/bin/python3 \
    docker.1ms.run/vllm/vllm-openai:v0.23.0-cu129-ubuntu2404 \
    -m vllm.entrypoints.openai.api_server \
        --model /usb/Qwen3.6-35BA3B-FP8 \
        --served-model-name Qwen \
        --max_model_len 262144 \
        --max-num-seqs 128 \
        --api-key gass-wlw-ai110 \
        --gpu-memory-utilization 0.6 \
        --host 0.0.0.0 \
        --port 8000 \
        --enable-auto-tool-choice \
        --tool-call-parser qwen3_coder \
        --trust-remote-code \
        --enable-chunked-prefill \
        --kv-cache-dtype fp8 \
        --enable-prefix-caching \
        --max-num-batched-tokens 16384


docker rm -f v_qwen36 2>/dev/null || true
docker run \
    --gpus all \
    --name v_qwen36 \
    -v /usb:/usb \
    -e CUDA_VISIBLE_DEVICES=0,1 \
    -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
    --ipc=host \
    --net=host \
    --restart=always \
    --entrypoint /usr/bin/python3 \
    -d \
    docker.1ms.run/vllm/vllm-openai:v0.23.0-cu129-ubuntu2404 \
    -m vllm.entrypoints.openai.api_server \
        --model /usb/Qwen3.6-35BA3B-FP8 \
        --served-model-name Qwen \
        --tensor-parallel-size 2 \
        --max-model-len 262144 \
        --max-num-seqs 8 \
        --api-key gass-wlw-ai110 \
        --gpu-memory-utilization 0.90 \
        --host 0.0.0.0 \
        --port 8000 \
        --enable-auto-tool-choice \
        --tool-call-parser qwen3_coder \
        --trust-remote-code \
        --enable-chunked-prefill \
        --kv-cache-dtype fp8 \
        --enable-prefix-caching \
        --max-num-batched-tokens 16384


MLLM  docker  model_servers  nohup.out  others  others.tar  readme.txt  result  run_mllm.sh  startfile.tar.gz  test.sh  ubuntu22.04-cu12.4-vllm-pt2.8-20251103.tar
(base) deep@trimps:~/env$ cat run_mllm.sh
export PATH="/home/deep/anaconda3/bin:$PATH"
export CUDA_LAUNCH_BLOCKING=1
export TORCH_USE_CUDA_DSA=1
cd /home/deep/env/model_servers/
python app.py \
    --address "0.0.0.0" \
    --port ${SERVER_PORT} \

