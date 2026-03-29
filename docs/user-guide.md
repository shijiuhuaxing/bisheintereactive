# 快速使用指南

## 🎯 快速开始（5分钟上手）

### 第一步：启动项目

**方法一：使用Python（推荐）**
```bash
# 在项目目录下运行
python -m http.server 8000
```

**方法二：使用Node.js**
```bash
# 在项目目录下运行
npx http-server -p 8000
```

### 第二步：打开浏览器

访问：`http://localhost:8000`

### 第三步：开始使用

1. 点击页面中央的 **🎤 麦克风按钮**
2. 允许浏览器访问麦克风权限
3. 开始说话（或等待3秒自动停止，模拟模式）
4. 查看识别结果和AI回答

## 📱 功能说明

### 当前DEMO功能

✅ **已实现**：
- 语音录制（真实麦克风或模拟模式）
- 模拟语音识别结果展示
- 模拟情绪分析展示
- 模拟AI情感化回答生成
- 虚拟形象情绪可视化
- 文本复制功能

⏳ **待集成API**：
- 真实语音识别API
- 真实情绪分析API
- 真实大模型API
- 真实语音合成API

## 🔧 切换到真实API

### 步骤1：准备后端API

确保您的后端API已经实现并运行，包含以下三个接口：
- `POST /api/speech-recognition` - 语音识别和情绪分析
- `POST /api/generate-response` - 大模型生成回答
- `POST /api/text-to-speech` - 文本转语音

### 步骤2：修改配置

打开 `app.js` 文件，找到第4-11行的配置：

```javascript
const API_CONFIG = {
    BASE_URL: 'http://localhost:5000',  // 改为您的API地址
    USE_MOCK_DATA: false,  // 改为 false
    ENDPOINTS: {
        SPEECH_RECOGNITION: '/api/speech-recognition',
        GENERATE_RESPONSE: '/api/generate-response',
        TEXT_TO_SPEECH: '/api/text-to-speech'
    }
};
```

### 步骤3：测试

1. 刷新浏览器页面
2. 点击录音按钮
3. 查看浏览器控制台（F12）查看API调用情况
4. 检查是否有错误信息

## 🐛 常见问题

### Q1: 无法访问麦克风？

**A**: 
- 确保浏览器允许麦克风权限
- 某些浏览器需要HTTPS才能访问麦克风
- 如果无法访问，系统会自动切换到模拟模式

### Q2: API调用失败？

**A**: 
- 检查 `BASE_URL` 是否正确
- 检查后端API是否正在运行
- 检查CORS配置是否正确
- 查看浏览器控制台的错误信息

### Q3: 如何测试API？

**A**: 
可以使用以下工具测试API：
- Postman
- curl命令
- 浏览器开发者工具的网络面板

### Q4: 如何自定义API端点？

**A**: 
修改 `API_CONFIG.ENDPOINTS` 中的路径即可。

## 📚 更多信息

详细文档请查看 `README.md` 文件。


