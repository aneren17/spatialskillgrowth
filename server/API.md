# 异常检测服务接口

本服务通过两个独立进程提供相同的异常检测接口。两个进程使用不同的多模态模型 Base URL、监听端口
和运行结果目录，可以同时启动。

## 1. 服务实例

| 启动脚本 | HTTP 端口 | 多模态模型 Base URL | 运行 ID |
|---|---:|---|---|
| `server/start_61.sh` | `18061` | `http://127.0.0.1:8861/v1` | `api_server_61` |
| `server/start_62.sh` | `18062` | `http://127.0.0.1:8862/v1` | `api_server_62` |

分别启动：

```bash
./server/start_61.sh
```

```bash
./server/start_62.sh
```

启动后可用项目内的测试脚本调用：

```bash
python server/test.py test/banner.mp4 banner --port 18061
python server/test.py test/banner.mp4 banner --port 18062
```

两个脚本都使用 `0.0.0.0` 监听，并固定使用一个 Uvicorn worker。Agent 在各自进程收到第一次请求时
延迟初始化。

默认根据同类别 `SKILL.md` 和当前抽样帧选择最合适的 2 条图片工作流。可在启动脚本前通过环境变量
调整：

| 环境变量 | 默认值 | 作用 |
|---|---:|---|
| `SPATIAL_SKILL_GROWTH_API_WORKFLOW_TOP_K` | `2` | 语义选择并行执行的图片工作流数量，必须大于 0。 |
| `SPATIAL_SKILL_GROWTH_API_ALL_WORKFLOWS` | `0` | 设为 `1` 时跳过 Top-K 语义选择，执行全部结构合格图片工作流。 |

例如将 18061 实例切换为全并行：

```bash
SPATIAL_SKILL_GROWTH_API_ALL_WORKFLOWS=1 ./server/start_61.sh
```

环境变量在 Agent 初始化时读取，修改后必须重启对应服务进程。

服务 run 会保留创建时的 Skill 快照。修改 `skills/spatialskillgrowth/` 后，应使用新 run ID 启动，
否则仍会读取旧快照：

```bash
SPATIAL_SKILL_GROWTH_API_RUN_ID=api_server_61_topk_v1 ./server/start_61.sh
```

## 2. 检测接口

```text
POST http://172.16.0.91:<18061|18062>/detect
Content-Type: multipart/form-data
```

两个端口的请求格式和响应格式完全相同。

### 输入字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | 文件 | 是 | 一张图片或一个短视频。文件名必须包含受支持的扩展名。 |
| `event_type` | 字符串 | 是 | 已确定的异常类别。推荐使用精确英文 ID，例如 `banner`、`fire`、`fall`。 |

支持的图片扩展名：

```text
.bmp .jpeg .jpg .png .webp
```

支持的视频扩展名：

```text
.avi .m4v .mkv .mov .mp4 .mpeg .mpg .webm
```

默认单文件上限为 256 MiB。服务不负责重新判断异常类别，只执行 `event_type` 指定类别的检测。

### 18061 端口调用示例

```bash
curl -X POST http://127.0.0.1:18061/detect \
  -F "file=@test/banner.mp4" \
  -F "event_type=banner"
```

### 18062 端口调用示例

```bash
curl -X POST http://127.0.0.1:18062/detect \
  -F "file=@test/banner.mp4" \
  -F "event_type=banner"
```

## 3. 成功输出

HTTP 状态码：`200`

```json
{
  "is_anomaly": 1,
  "threshold": 0.66
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `is_anomaly` | 整数 | `1` 表示检测到异常，`0` 表示未检测到异常。 |
| `threshold` | 浮点数 | embedding 返回的判定阈值；其他图片工作流覆盖为异常时返回 `1.0`。 |

视频推理会并行执行原视频 embedding 工作流和默认由 `SKILL.md` 选出的 Top-K 图片工作流，并用
确定性 OR 汇总：任一有效工作流判断异常，最终 `is_anomaly` 即为 `1`。全工作流模式只改变图片
工作流候选数量，不改变原视频 embedding 通道和 OR 规则。

## 4. 错误输出

错误响应使用 FastAPI 的统一格式：

```json
{
  "detail": "错误原因"
}
```

| HTTP 状态码 | 常见原因 |
|---:|---|
| `400` | `event_type` 不受支持、文件扩展名不受支持、文件为空或超过大小限制。 |
| `422` | 缺少 `file` 或 `event_type` 表单字段。 |
| `500` | Agent 初始化或异常检测执行失败。 |
| `502` | 下游工具没有返回可接受的异常判断或 embedding 阈值。 |

服务关闭了 Swagger、ReDoc 和 OpenAPI 路由，目前只提供 `POST /detect` 业务接口。
