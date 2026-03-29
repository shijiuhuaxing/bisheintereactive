# 情智兼备的虚拟陪伴生成系统 - DEMO演示

## 📋 项目简介

这是一个基于多模态情绪感知的智能虚拟陪伴系统DEMO。系统能够通过语音输入识别用户情绪，并生成带有情感色彩的智能回应。

**项目名称**：情智兼备的虚拟陪伴生成关键技术及互动系统研发

## ✨ 功能特性

- 🎤 **语音输入**：支持实时语音录制和识别
- 😊 **情绪感知**：基于语音内容进行情绪分析
- 💬 **智能回应**：大模型根据情绪生成应景的情感化回答
- 🔊 **语音输出**：支持将回答转换为语音播放（需API支持）
- 👤 **虚拟形象**：可视化展示当前情绪状态
- 📱 **响应式设计**：支持桌面和移动设备

## 🚀 快速开始

### 方法一：直接打开（最简单）

直接在浏览器中打开 `index.html` 文件即可使用。

**注意**：由于浏览器安全限制，某些功能（如麦克风访问）可能需要使用本地服务器运行。

### 📱 移动端使用

页面已优化支持移动端访问，可以在手机浏览器中正常使用：

1. **通过局域网访问**：
   - 确保手机和电脑在同一WiFi网络
   - 在电脑上启动服务器（如 `python -m http.server 8000`）
   - 在手机浏览器访问：`http://电脑IP地址:8000`
   - 例如：`http://192.168.1.100:8000`

2. **移动端特性**：
   - ✅ 响应式布局，自动适配手机屏幕
   - ✅ 触摸友好的按钮和交互
   - ✅ 优化的字体大小和间距
   - ✅ 支持移动端麦克风录音
   - ✅ 防止意外缩放和选择

3. **获取电脑IP地址**：
   - **Windows**: 打开命令提示符，输入 `ipconfig`，查找 IPv4 地址
   - **macOS/Linux**: 打开终端，输入 `ifconfig` 或 `ip addr`，查找局域网IP

### 方法二：使用Python本地服务器（推荐）

```bash
# Python 3.x
python -m http.server 8000

# 或者 Python 2.x
python -m SimpleHTTPServer 8000
```

然后在浏览器中访问：`http://localhost:8000`

### 方法三：使用Node.js服务器

```bash
# 安装 http-server（如果未安装）
npm install -g http-server

# 启动服务器
http-server -p 8000
```

然后在浏览器中访问：`http://localhost:8000`

## 📖 使用方法

### 基本操作流程

1. **开始录音**
   - 点击页面中央的麦克风按钮开始录音
   - 按钮会变成红色并显示"点击停止录音"
   - 页面会显示录音动画和状态提示

2. **停止录音**
   - 再次点击按钮停止录音
   - 系统会自动处理录音内容

3. **查看结果**
   - **语音识别结果**：显示在"语音识别结果"区域
   - **AI回答**：显示在"AI情感回应"区域
   - **情绪分析**：以标签形式展示在情绪分析区域
   - **虚拟形象**：根据情绪变化显示不同的背景颜色

4. **播放语音**
   - 点击"播放语音"按钮可以播放AI回答
   - ⚠️ 当前为DEMO版本，需要连接TTS API才能实际播放

5. **复制文本**
   - 点击"复制文本"按钮可以复制AI回答到剪贴板

### 界面说明

- **左侧区域**：虚拟陪伴形象展示区，显示当前情绪状态
- **右侧区域**：交互控制区，包含语音输入和AI回答输出
- **底部状态栏**：显示系统状态和API连接状态

## ⚙️ 当前状态

⚠️ **当前版本为DEMO演示版本**，使用模拟数据进行展示，不连接真实API。

系统默认使用模拟数据，您可以通过修改 `app.js` 文件中的 `API_CONFIG` 配置来切换到真实API模式。

## 🔌 API集成指南

### 快速集成 Qwen3-ASR

如果您想使用阿里云的 Qwen3-ASR 进行语音识别，请查看 **`Qwen3-ASR集成指南.md`** 文件，其中包含详细的集成步骤和示例代码。

**快速开始**：
1. 获取 DashScope API Key
2. 安装依赖：`pip install -r requirements.txt`
3. 设置环境变量：`export DASHSCOPE_API_KEY="your_api_key"`
4. 运行后端：`python backend_example.py`
5. 修改前端配置（见下方）

### 第一步：配置API地址

打开 `app.js` 文件，找到文件开头的 `API_CONFIG` 配置：

```javascript
const API_CONFIG = {
    BASE_URL: 'http://localhost:5000',  // 修改为您的后端API地址
    USE_MOCK_DATA: true,  // 改为 false 以使用真实API
    ENDPOINTS: {
        SPEECH_RECOGNITION: '/api/speech-recognition',
        GENERATE_RESPONSE: '/api/generate-response',
        TEXT_TO_SPEECH: '/api/text-to-speech'
    }
};
```

**修改步骤**：
1. 将 `USE_MOCK_DATA` 改为 `false`
2. 将 `BASE_URL` 修改为您的后端API服务器地址

### 第二步：API接口规范

系统需要三个主要API接口：

#### 1. 语音识别与情绪分析 API

**端点**：`POST /api/speech-recognition`

**请求格式**：
```
Content-Type: multipart/form-data

FormData {
  audio: File (音频文件，支持 wav/mp3/m4a 等格式)
}
```

**响应格式**：
```json
{
  "text": "识别出的文本内容",
  "emotion": {
    "emotion": "开心",
    "confidence": 0.85,
    "tags": ["快乐", "积极", "轻松"]
  }
}
```

**字段说明**：
- `text`: 语音识别出的文本内容（字符串）
- `emotion.emotion`: 主要情绪类型（字符串，如：开心、难过、疲惫、平静、感激等）
- `emotion.confidence`: 情绪识别置信度（0-1之间的浮点数）
- `emotion.tags`: 情绪标签数组（字符串数组）

#### 2. 大模型生成回答 API

**端点**：`POST /api/generate-response`

**请求格式**：
```json
{
  "text": "用户输入的文本",
  "emotion": "开心",
  "emotion_confidence": 0.85,
  "context": ["快乐", "积极", "轻松"]
}
```

**响应格式**：
```json
{
  "response": "AI生成的带有情感的回答文本",
  "emotion_style": "开心"
}
```

**字段说明**：
- `text`: 用户输入的文本内容
- `emotion`: 识别出的主要情绪
- `emotion_confidence`: 情绪识别置信度
- `context`: 情绪标签数组
- `response`: AI生成的回答文本（应该根据情绪生成相应的情感化回答）

#### 3. 文本转语音 API

**端点**：`POST /api/text-to-speech`

**请求格式**：
```json
{
  "text": "要转换的文本",
  "emotion": "开心"
}
```

**响应格式**：
```json
{
  "audio_url": "http://example.com/audio/xxx.mp3"
}
```

**字段说明**：
- `text`: 要转换为语音的文本
- `emotion`: 情绪类型（用于生成带有情感的语音）
- `audio_url`: 生成的音频文件URL（应该可以直接通过浏览器播放）

### 第三步：后端实现示例

#### Python Flask 示例

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求

@app.route('/api/speech-recognition', methods=['POST'])
def speech_recognition():
    """
    语音识别和情绪分析接口
    """
    if 'audio' not in request.files:
        return jsonify({'error': '没有上传音频文件'}), 400
    
    audio_file = request.files['audio']
    
    # TODO: 调用语音识别API（如百度、讯飞、Azure等）
    # text = recognize_speech(audio_file)
    
    # TODO: 调用情绪分析模型
    # emotion = analyze_emotion(audio_file, text)
    
    # 示例返回（实际应该调用真实API）
    return jsonify({
        'text': '识别出的文本',
        'emotion': {
            'emotion': '开心',
            'confidence': 0.85,
            'tags': ['快乐', '积极']
        }
    })

@app.route('/api/generate-response', methods=['POST'])
def generate_response():
    """
    大模型生成情感化回答接口
    """
    data = request.json
    text = data.get('text', '')
    emotion = data.get('emotion', '平静')
    emotion_confidence = data.get('emotion_confidence', 0.5)
    context = data.get('context', [])
    
    # TODO: 调用大模型API（如OpenAI GPT、Claude、文心一言等）
    # 注意：prompt应该包含情绪信息，确保生成情感化的回答
    # prompt = f"用户说：{text}，情绪是{emotion}，请生成一个温暖、共情、带有{emotion}情感的回答。"
    # response = llm.generate(prompt)
    
    # 示例返回（实际应该调用真实API）
    return jsonify({
        'response': 'AI生成的回答',
        'emotion_style': emotion
    })

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """
    文本转语音接口
    """
    data = request.json
    text = data.get('text', '')
    emotion = data.get('emotion', 'neutral')
    
    # TODO: 调用TTS API（如Azure、百度、讯飞等）
    # audio_url = tts.generate(text, emotion=emotion)
    
    # 示例返回（实际应该调用真实API）
    return jsonify({
        'audio_url': 'http://example.com/audio/xxx.mp3'
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

#### 安装依赖

```bash
pip install flask flask-cors
```

### 第四步：测试API连接

1. 启动后端服务器（如上面的Flask示例）
2. 修改 `app.js` 中的 `API_CONFIG`：
   ```javascript
   const API_CONFIG = {
       BASE_URL: 'http://localhost:5000',
       USE_MOCK_DATA: false,  // 改为 false
       // ...
   };
   ```
3. 刷新前端页面，测试API连接
4. 查看浏览器控制台（F12）查看API调用日志

### 常见问题

#### 1. CORS跨域问题

如果遇到跨域错误，确保后端配置了CORS：

```python
from flask_cors import CORS
CORS(app)  # Flask
```

或使用其他框架的CORS中间件。

#### 2. 音频格式问题

确保后端API支持常见的音频格式（wav、mp3、m4a等）。前端使用 `MediaRecorder` API录制，默认格式可能因浏览器而异。

#### 3. API响应格式

确保API响应格式严格按照上述规范，否则前端可能无法正确解析。

## 🛠️ 技术栈

- **前端**：HTML5, CSS3, JavaScript (ES6+)
- **音频处理**：Web Audio API, MediaRecorder API
- **UI设计**：响应式设计，渐变色彩，动画效果
- **后端**：Python Flask（示例），可替换为其他框架

## 📁 文件结构

```
.
├── index.html          # 主页面
├── styles.css          # 样式文件
├── app.js              # 前端逻辑和API集成代码
├── README.md           # 说明文档（本文件）
└── test.py             # 测试文件（可忽略）
```

## ⚠️ 注意事项

1. **浏览器兼容性**：建议使用Chrome、Edge等现代浏览器
2. **麦克风权限**：首次使用需要授权麦克风访问权限
3. **HTTPS要求**：某些浏览器功能（如MediaRecorder）可能需要HTTPS环境
4. **CORS配置**：后端API需要配置CORS以允许前端跨域请求
5. **API地址**：确保前端可以访问后端API地址（注意防火墙和网络设置）

## 🔮 后续开发建议

### 1. 情绪感知模块
- 集成面部表情识别（如果使用视频输入）
- 集成语音情感识别模型（如使用深度学习模型）
- 多模态信息融合算法

### 2. 大模型集成
- 选择合适的LLM（GPT-4、Claude、文心一言、通义千问等）
- 设计prompt工程，确保情感化输出
- 实现上下文记忆功能（对话历史）
- 优化回答质量和相关性

### 3. 语音合成
- 选择TTS服务（Azure、百度、讯飞、ElevenLabs等）
- 实现情感化语音合成
- 优化语音自然度和情感表达

### 4. 虚拟形象
- 集成3D虚拟形象（如Live2D、VRM、Ready Player Me等）
- 实现表情和动作驱动
- 添加更多交互效果和动画

### 5. 性能优化
- 实现音频流式处理
- 优化API调用延迟
- 添加缓存机制
- 实现离线功能

## 📝 代码说明

### API集成代码位置

所有API集成相关的代码都在 `app.js` 文件中：

- **API配置**：文件开头的 `API_CONFIG` 对象
- **API调用类**：`APIIntegration` 类（包含三个静态方法）
- **实际调用位置**：
  - `processAudio()` 方法：调用语音识别API
  - `generateResponse()` 方法：调用大模型API
  - `playResponse()` 方法：调用TTS API

### 切换模拟/真实API

只需修改 `API_CONFIG.USE_MOCK_DATA` 的值：
- `true`：使用模拟数据（DEMO模式）
- `false`：使用真实API

## 📄 许可证

本项目为毕业设计DEMO，仅供学习和演示使用。

## 📧 联系方式

如有问题或建议，欢迎反馈！

---

**祝您使用愉快！** 🎉
