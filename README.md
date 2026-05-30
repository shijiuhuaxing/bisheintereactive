# 情智兼备的虚拟陪伴生成系统

一个面向毕业设计的多模态虚拟陪伴交互系统原型，当前已经打通“语音输入 -> 情绪识别 -> 情感对话生成 -> 情感语音输出 -> 虚拟形象反馈”的完整演示链路。

## 项目简介

本项目聚焦于虚拟陪伴场景中的多模态情绪感知与情感生成，目标是构建一个能够理解用户表情、语音和文本情绪，并给出带有陪伴感回应的实时交互系统。

当前版本已经具备：

- 语音输入与语音识别
- 文本情绪识别
- 语音情绪识别
- 摄像头表情识别
- 多模态情绪融合
- 情感化文本回复生成
- 情感语音生成与播放
- 页面内连续对话上下文记忆

## 当前已接入的模型与服务

- 语音识别：`DashScope / Qwen ASR`
- 文本情绪识别：`Qwen API`
- 语音情绪识别：`superb/wav2vec2-base-superb-er`
- 表情识别：`FERPlus ONNX`
- 对话生成：`Qwen API`
- 情感语音生成：`Qwen3-TTS`

## 技术栈

### 前端

- `HTML / CSS / JavaScript`
- `MediaDevices API`
- `AudioContext`

### 后端

- `Python`
- `Flask`
- `flask-cors`
- `python-dotenv`

### 模型与推理

- `PyTorch`
- `transformers`
- `onnxruntime`
- `OpenCV`
- `librosa`
- `soundfile`
- `dashscope`

## 目录结构

```text
.
|-- frontend/              # 前端页面与静态资源
|-- backend/               # Flask 后端与各模块服务
|-- docs/                  # 架构说明、使用指南、论文相关文档
|-- data/                  # 数据目录
|-- models/                # 本地模型与配置
|-- scripts/               # 启动脚本与辅助脚本
|-- logs/                  # 运行日志
`-- outputs/               # 生成音频、报告、截图等输出
```

## 快速开始

### 1. 安装依赖

推荐使用项目中的 Python 3.11 虚拟环境，或自行准备兼容环境后执行：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填写自己的 `DASHSCOPE_API_KEY`：

```env
APP_HOST=0.0.0.0
APP_PORT=5000
APP_DEBUG=false
USE_MOCK_SERVICES=false

ASR_PROVIDER=qwen_dashscope
TEXT_EMOTION_PROVIDER=qwen_dashscope
TEXT_EMOTION_MODEL=qwen-turbo
SPEECH_EMOTION_PROVIDER=wav2vec2_superb
SPEECH_EMOTION_MODEL=superb/wav2vec2-base-superb-er

DASHSCOPE_API_KEY=你的API Key
DASHSCOPE_ASR_MODEL=paraformer-realtime-v2

LLM_PROVIDER=qwen_dashscope
LLM_MODEL=qwen-turbo

TTS_PROVIDER=qwen_dashscope
DASHSCOPE_TTS_MODEL=qwen3-tts-instruct-flash-realtime
DASHSCOPE_TTS_VOICE=Cherry
DASHSCOPE_TTS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
```

### 3. 启动后端

推荐直接运行：

```bat
scripts\run_backend.bat
```

或手动执行：

```bash
.venv311\Scripts\python.exe backend_example.py
```

### 4. 启动实时会话服务

如果需要启用 WebSocket 实时会话链路，另开一个终端运行：

```bat
scripts\run_realtime.bat
```

实时服务默认监听：`ws://127.0.0.1:8001/ws/realtime`。如果该服务未启动，前端会自动回退到 HTTP 回合式接口。

### 5. 启动前端

推荐直接运行：

```bat
scripts\run_frontend.bat
```

前端脚本会使用自定义静态服务，以正确返回 `.mjs` 和 `.glb` 等 3D 资源的 MIME 类型。若需要手动启动，可执行：

```bash
python scripts/frontend_server.py
```

### 6. 打开页面

- 前端：`http://127.0.0.1:8000`
- 后端健康检查：`http://127.0.0.1:5000/api/health`
- 实时服务健康检查：`http://127.0.0.1:8001/health`

## 使用说明

### 基本流程

1. 打开前端页面
2. 允许麦克风和摄像头权限
3. 如需实时表情识别，点击“开启实时表情识别”
4. 点击录音按钮，说出当前状态
5. 等待系统完成识别、融合、对话生成和语音输出

### 连续对话说明

- 同一页面内最近几轮对话会保留上下文
- 页面刷新后，对话上下文会被重置

## 当前功能说明

### 交互模块

- 录音输入
- 摄像头采样
- 实时表情识别结果展示
- 语音识别文本展示

### 回应模块

- 虚拟形象情绪变化
- 当前融合情绪展示
- 陪伴式文本回应
- 情感语音播放
- 多模态情感识别结果展示

## 当前性能说明

以下为当前原型阶段的典型观察值，实际表现受网络、电脑性能、模型首次加载等影响：

- 实时表情识别刷新：约每 `1.2s` 一次
- 对话生成：通常 `1s` 左右到数秒
- Qwen3-TTS：常见耗时约 `2s - 5s`
- 同一页面内上下文记忆：即时生效

## 注意事项

- `.env` 不要提交到 Git 仓库
- 当前多项能力依赖 DashScope / Qwen API，需保证网络可用
- `speech emotion` 当前采用英文基线模型，中文场景下仍有优化空间
- 当前 TTS 为“合成完成后播放”，还不是完全流式播放

## 重要文档

- `docs/architecture.md`：系统架构说明
- `docs/realtime-roadmap.md`：实时化升级路线
- `docs/当前项目说明与使用指南.md`：完整中文使用手册
- `docs/api.md`：接口接入说明

## 后续可继续开发方向

- 优化中文语音情绪识别模型
- 将 TTS 升级为流式播放
- 增强虚拟形象动画表现
- 增加更完整的对话历史展示
- 完成实验记录、消融对比和论文图表输出
