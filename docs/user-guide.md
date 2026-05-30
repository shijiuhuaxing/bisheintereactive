# 多模态虚拟陪伴系统使用说明

本文档说明如何在本地启动和测试“面向虚拟陪伴场景的多模态情绪感知与具身化反馈系统”。系统由 Flask 后端、FastAPI WebSocket 实时服务和前端静态页面三部分组成。

## 1. 环境准备

建议使用 Python 3.11 或以上版本。首次运行前，在项目根目录安装依赖：

```bat
pip install -r requirements.txt
```

如需使用真实 DashScope 服务，请复制环境变量模板：

```bat
copy .env.example .env
```

然后在 `.env` 中填写：

```env
DASHSCOPE_API_KEY=你的DashScope密钥
USE_MOCK_SERVICES=false
```

注意：`.env` 只用于本地运行，已被 `.gitignore` 忽略，不应提交到仓库。

## 2. 启动服务

系统需要启动三个服务，建议分别打开三个终端。

### 2.1 启动 Flask 后端

```bat
scripts\run_backend.bat
```

默认地址：

```text
http://127.0.0.1:5000
```

健康检查：

```text
http://127.0.0.1:5000/api/health
```

### 2.2 启动 WebSocket 实时服务

```bat
scripts\run_realtime.bat
```

默认地址：

```text
ws://127.0.0.1:8001/ws/realtime
```

健康检查：

```text
http://127.0.0.1:8001/health
```

### 2.3 启动前端页面

```bat
scripts\run_frontend.bat
```

前端地址：

```text
http://127.0.0.1:8000
```

前端使用自定义静态服务，以保证 `.mjs`、`.glb` 等 3D 资源的 MIME 类型正确。

## 3. 使用流程

1. 打开前端页面 `http://127.0.0.1:8000`。
2. 等待系统状态显示为“实时链路已连接”。
3. 如需表情输入，点击“开启实时表情识别”，允许浏览器访问摄像头。
4. 点击录音按钮，说出当前状态或想交流的内容。
5. 系统会依次展示：
   - 语音识别文本；
   - 文本、语音、表情三类情绪结果；
   - 多模态融合结果；
   - 大模型生成的陪伴式回应。
6. 点击“播放语音”可以播放 TTS 结果；若真实语音合成失败，前端会回退到浏览器朗读。

## 4. 实时处理说明

前端优先使用 WebSocket 实时链路。实时链路会分阶段返回结果：

```text
session.ready -> turn.started -> asr.final -> emotion.update -> response.text -> turn.done -> tts.ready
```

其中 `response.text` 返回后，前端会立即显示回复并启用播放按钮，不必等待 TTS 完成。语音情绪和 TTS 生成会在后台继续处理，完成后再更新页面状态。

如果 WebSocket 服务不可用，前端会自动回退到 HTTP 回合式接口。

## 5. 多模态融合说明

系统融合层采用不确定性感知时序自适应融合方法。前端会展示以下调试信息：

- 模态质量 `quality`
- 模态不确定性 `uncertainty`
- 动态权重 `weight`
- 时序先验 `temporal_prior`
- 一致性奖励 `agreement_bonus`
- 冲突惩罚 `conflict_penalty`
- 候选情绪 `top_candidates`

这些字段用于说明系统如何根据当前输入质量、模态冲突和历史状态得到最终融合情绪。

## 6. 虚拟形象说明

前端会加载 3D 虚拟形象资源，并根据融合情绪切换状态。语音播放或浏览器朗读时，虚拟形象会启动说话口型动画；播放结束后自动闭嘴。

若 3D 模型加载失败，页面会保留 2D 形象作为兜底，不影响情绪识别、回复生成和语音播放主流程。

## 7. 常见问题

### 7.1 语音识别不是我说的内容

检查后端健康接口中的配置：

```text
http://127.0.0.1:5000/api/health
```

如果显示 `use_mock_services: true` 或 `dashscope_configured: false`，说明没有正确配置 `.env` 中的 `DASHSCOPE_API_KEY`。

### 7.2 语音生成失败

可能原因包括网络波动、DashScope 配额不足或 TTS 接口暂时不可用。此时前端会自动回退浏览器朗读。

### 7.3 3D 形象加载慢

首次加载需要下载和解析 GLB 模型，通常需要等待数秒。页面已加入预加载和“3D形象加载中”提示。后续刷新会利用浏览器缓存，速度会更快。

### 7.4 页面没有连接实时链路

确认实时服务已启动：

```text
http://127.0.0.1:8001/health
```

如果未启动，前端会自动回退到 HTTP 接口。

## 8. 上传 GitHub 前注意事项

不要提交以下本地文件或目录：

```text
.env
.venv*/
logs/
outputs/
__pycache__/
*.pyc
```

模型和前端静态资源可随项目提交；如果未来模型文件超过 GitHub 单文件限制，应改用 Git LFS 或在 README 中提供下载说明。
