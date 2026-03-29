# Qwen3-ASR API 集成指南

## 📋 概述

Qwen3-ASR-Toolkit 是一个高性能的Python工具包，用于调用阿里云DashScope的Qwen-ASR API进行语音识别。本指南将说明如何将这个工具集成到您的虚拟陪伴系统中。

## 🔑 前置准备

### 1. 获取 DashScope API Key

1. 访问 [DashScope控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 创建API Key
4. 设置环境变量（推荐）：

**Linux/macOS:**
```bash
export DASHSCOPE_API_KEY="your_api_key_here"
# 永久设置，添加到 ~/.bashrc 或 ~/.zshrc
echo 'export DASHSCOPE_API_KEY="your_api_key_here"' >> ~/.bashrc
```

**Windows (PowerShell):**
```powershell
$env:DASHSCOPE_API_KEY="your_api_key_here"
```

**Windows (系统环境变量):**
- 搜索"编辑系统环境变量"
- 添加用户变量 `DASHSCOPE_API_KEY`

### 2. 安装依赖

```bash
# 安装 Qwen3-ASR-Toolkit
pip install qwen3-asr-toolkit

# 或者安装 DashScope SDK（如果直接使用SDK）
pip install dashscope
```

### 3. 安装 FFmpeg（必需）

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
- 从 [FFmpeg官网](https://ffmpeg.org/download.html) 下载
- 解压并添加到系统PATH环境变量

## 🚀 集成方案

### 方案一：使用 Qwen3-ASR-Toolkit（推荐用于长音频）

这个工具适合处理较长的音频文件（超过3分钟），它会自动分割音频并并行处理。

#### 后端实现示例（Flask）

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import subprocess
import json

app = Flask(__name__)
CORS(app)

# 从环境变量获取API Key
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')

@app.route('/api/speech-recognition', methods=['POST'])
def speech_recognition():
    """
    语音识别和情绪分析接口
    使用 Qwen3-ASR-Toolkit 进行语音识别
    """
    if 'audio' not in request.files:
        return jsonify({'error': '没有上传音频文件'}), 400
    
    audio_file = request.files['audio']
    
    # 创建临时文件保存上传的音频
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        audio_file.save(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        # 使用 qwen3-asr 命令行工具进行识别
        # 注意：这里需要确保 qwen3-asr 命令在系统PATH中
        result = subprocess.run(
            [
                'qwen3-asr',
                '-i', tmp_path,
                '-key', DASHSCOPE_API_KEY,
                '-j', '4',  # 使用4个并发线程
                '-s'  # 静默模式
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': '语音识别失败',
                'details': result.stderr
            }), 500
        
        # 读取识别结果（qwen3-asr会生成 .txt 文件）
        txt_path = tmp_path.replace('.wav', '.txt')
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                recognized_text = f.read().strip()
        else:
            # 如果文件不存在，尝试从stdout获取
            recognized_text = result.stdout.strip()
        
        # TODO: 这里需要添加情绪分析
        # 可以使用情绪分析模型或API来分析 recognized_text 和音频
        emotion_data = analyze_emotion(recognized_text, tmp_path)
        
        return jsonify({
            'text': recognized_text,
            'emotion': emotion_data
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': '处理超时'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        txt_path = tmp_path.replace('.wav', '.txt')
        if os.path.exists(txt_path):
            os.unlink(txt_path)

def analyze_emotion(text, audio_path):
    """
    情绪分析函数
    这里需要实现您的情绪分析逻辑
    可以使用：
    1. 文本情绪分析模型（如BERT情感分析）
    2. 语音情绪分析模型
    3. 第三方情绪分析API
    """
    # 示例：简单的基于关键词的情绪分析
    positive_words = ['开心', '高兴', '快乐', '兴奋', '满意']
    negative_words = ['难过', '悲伤', '沮丧', '失望', '疲惫']
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        emotion = '开心'
        confidence = 0.7 + min(positive_count * 0.1, 0.2)
        tags = ['快乐', '积极']
    elif negative_count > positive_count:
        emotion = '难过'
        confidence = 0.7 + min(negative_count * 0.1, 0.2)
        tags = ['悲伤', '需要安慰']
    else:
        emotion = '平静'
        confidence = 0.6
        tags = ['平静', '中性']
    
    return {
        'emotion': emotion,
        'confidence': confidence,
        'tags': tags
    }

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

### 方案二：直接使用 DashScope SDK（推荐用于短音频）

对于实时语音识别（通常音频较短），可以直接使用 DashScope SDK。

#### 安装 SDK

```bash
pip install dashscope
```

#### 后端实现示例

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import dashscope
from dashscope.audio.asr import Recognition
import os
import tempfile

app = Flask(__name__)
CORS(app)

# 设置API Key
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')

@app.route('/api/speech-recognition', methods=['POST'])
def speech_recognition():
    """
    语音识别接口 - 使用 DashScope SDK
    注意：官方API限制音频长度不超过3分钟
    """
    if 'audio' not in request.files:
        return jsonify({'error': '没有上传音频文件'}), 400
    
    audio_file = request.files['audio']
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        audio_file.save(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        # 调用 DashScope ASR API
        recognition = Recognition()
        
        with open(tmp_path, 'rb') as f:
            result = recognition.call(
                model='paraformer-realtime-v2',  # 或 'paraformer-v2' 用于非实时
                format='wav',
                audio=f.read()
            )
        
        if result.status_code == 200:
            recognized_text = result.output.sentence
            
            # 情绪分析
            emotion_data = analyze_emotion(recognized_text, tmp_path)
            
            return jsonify({
                'text': recognized_text,
                'emotion': emotion_data
            })
        else:
            return jsonify({
                'error': '语音识别失败',
                'details': result.message
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def analyze_emotion(text, audio_path):
    """
    情绪分析函数
    同方案一
    """
    # ... 实现情绪分析逻辑
    pass

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

## 📝 完整后端示例

创建一个完整的 `backend.py` 文件：

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import dashscope
from dashscope.audio.asr import Recognition
import os
import tempfile
import json

app = Flask(__name__)
CORS(app)

# 配置
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY', 'your_api_key_here')

@app.route('/api/speech-recognition', methods=['POST'])
def speech_recognition():
    """语音识别和情绪分析"""
    if 'audio' not in request.files:
        return jsonify({'error': '没有上传音频文件'}), 400
    
    audio_file = request.files['audio']
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        audio_file.save(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        # 调用 DashScope ASR
        recognition = Recognition()
        
        with open(tmp_path, 'rb') as f:
            result = recognition.call(
                model='paraformer-realtime-v2',
                format='wav',
                audio=f.read()
            )
        
        if result.status_code == 200:
            recognized_text = result.output.sentence
            
            # 情绪分析
            emotion_data = analyze_emotion_simple(recognized_text)
            
            return jsonify({
                'text': recognized_text,
                'emotion': emotion_data
            })
        else:
            return jsonify({
                'error': '语音识别失败',
                'details': result.message
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def analyze_emotion_simple(text):
    """简单的情绪分析（基于关键词）"""
    text_lower = text.lower()
    
    # 情绪关键词映射
    emotion_keywords = {
        '开心': ['开心', '高兴', '快乐', '兴奋', '满意', '愉快', '欣喜'],
        '难过': ['难过', '悲伤', '沮丧', '失望', '痛苦', '伤心'],
        '疲惫': ['累', '疲惫', '疲倦', '困', '疲劳', '乏力'],
        '感激': ['谢谢', '感谢', '感激', '感恩'],
        '平静': ['平静', '正常', '一般']
    }
    
    scores = {}
    for emotion, keywords in emotion_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        scores[emotion] = score
    
    # 找到得分最高的情绪
    max_emotion = max(scores, key=scores.get)
    max_score = scores[max_emotion]
    
    # 计算置信度
    total_score = sum(scores.values())
    confidence = max_score / max(total_score, 1) if total_score > 0 else 0.5
    
    # 生成标签
    tags = []
    if max_emotion == '开心':
        tags = ['快乐', '积极', '轻松']
    elif max_emotion == '难过':
        tags = ['悲伤', '需要倾听', '情绪低落']
    elif max_emotion == '疲惫':
        tags = ['压力', '疲惫', '需要安慰']
    elif max_emotion == '感激':
        tags = ['感谢', '温暖', '积极']
    else:
        tags = ['平静', '中性']
    
    return {
        'emotion': max_emotion,
        'confidence': min(confidence + 0.3, 0.95),  # 确保置信度在合理范围
        'tags': tags
    }

@app.route('/api/generate-response', methods=['POST'])
def generate_response():
    """大模型生成回答"""
    data = request.json
    text = data.get('text', '')
    emotion = data.get('emotion', '平静')
    
    # TODO: 调用大模型API（OpenAI、Claude、文心一言等）
    # 这里使用模拟数据
    mock_responses = {
        "开心": "太好了！听到你心情不错，我也为你感到高兴呢！😊",
        "难过": "我感受到了你的难过，这一定很不容易。如果你愿意的话，可以和我详细说说。💙",
        "疲惫": "我理解你的感受，工作压力确实不容易。要不要先休息一下？",
        "感激": "听到你这么说，我也很感动。能够陪伴你，对我来说也是一件很幸福的事情。💙",
        "平静": "当然可以！我很乐意和你聊天。你想聊什么呢？😊"
    }
    
    response_text = mock_responses.get(emotion, mock_responses["平静"])
    
    return jsonify({
        'response': response_text,
        'emotion_style': emotion
    })

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """文本转语音"""
    data = request.json
    text = data.get('text', '')
    emotion = data.get('emotion', 'neutral')
    
    # TODO: 调用TTS API（Azure、百度、讯飞等）
    # 这里返回模拟URL
    return jsonify({
        'audio_url': 'http://example.com/audio/xxx.mp3'
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

## 🔧 使用步骤

### 1. 安装依赖

```bash
pip install flask flask-cors dashscope
```

### 2. 设置环境变量

```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

### 3. 运行后端

```bash
python backend.py
```

### 4. 修改前端配置

在 `app.js` 中修改：

```javascript
const API_CONFIG = {
    BASE_URL: 'http://localhost:5000',
    USE_MOCK_DATA: false,  // 改为 false
    // ...
};
```

### 5. 测试

1. 启动后端服务器
2. 打开前端页面
3. 点击录音按钮
4. 查看识别结果

## ⚠️ 注意事项

1. **音频格式**：确保音频格式为 WAV、MP3 等常见格式
2. **音频长度**：
   - DashScope SDK 直接调用：限制3分钟以内
   - Qwen3-ASR-Toolkit：可以处理任意长度（会自动分割）
3. **API配额**：注意 DashScope API 的调用次数和费用限制
4. **错误处理**：添加适当的错误处理和重试机制
5. **安全性**：不要在前端代码中暴露 API Key

## 🔄 高级功能

### 使用 Qwen3-ASR-Toolkit 处理长音频

如果您的应用需要处理较长的音频（如会议录音、讲座等），可以使用 Qwen3-ASR-Toolkit：

```python
import subprocess
import os

def transcribe_long_audio(audio_path, api_key):
    """使用 qwen3-asr 工具处理长音频"""
    result = subprocess.run(
        [
            'qwen3-asr',
            '-i', audio_path,
            '-key', api_key,
            '-j', '4',  # 并发线程数
            '-d', '120',  # 目标分块时长（秒）
            '-s'  # 静默模式
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        # 读取生成的 .txt 文件
        txt_path = audio_path.replace('.wav', '.txt')
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    else:
        raise Exception(f"识别失败: {result.stderr}")
```

## 📚 参考资源

- [DashScope 官方文档](https://help.aliyun.com/zh/dashscope/)
- [Qwen3-ASR-Toolkit GitHub](https://github.com/QwenLM/Qwen3-ASR-Toolkit)
- [DashScope Python SDK](https://help.aliyun.com/zh/dashscope/developer-reference/api-details-9)

## 🎯 下一步

1. 实现更精确的情绪分析（使用深度学习模型）
2. 集成大模型API生成情感化回答
3. 集成TTS API实现语音输出
4. 优化音频处理性能


