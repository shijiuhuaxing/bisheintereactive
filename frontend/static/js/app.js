// 虚拟陪伴系统前端交互逻辑
// 注意：当前默认使用 mock 数据，真实 API 集成请参考 docs 目录。

class VirtualCompanionDemo {
    constructor() {
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.cameraStream = null;
        this.realtimeFaceEnabled = false;
        this.faceLoopTimer = null;
        this.audioChunks = [];
        this.audioContext = null;
        this.audioSourceNode = null;
        this.audioProcessorNode = null;
        this.recordedAudioBuffers = [];
        this.recordingSampleRate = 16000;
        this.pendingFrameBlob = null;
        this.currentResponseText = '';
        this.currentEmotionData = null;
        this.currentDialogueResult = null;
        this.conversationHistory = [];
        this.latestFaceEmotion = null;
        this.faceEmotionHistory = [];
        this.faceSmoothingWindow = 4;
        this.currentTtsAudioUrl = '';
        this.pendingTtsPromise = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateSystemStatus('系统就绪');
        this.updateCameraStatus('待启用');
        this.updateCameraEmotionResult(null);
        this.checkAPIStatus();
    }

    setupEventListeners() {
        // 录音按钮
        const recordBtn = document.getElementById('recordBtn');
        recordBtn.addEventListener('click', () => this.toggleRecording());

        // 播放按钮
        const playBtn = document.getElementById('playBtn');
        playBtn.addEventListener('click', () => this.playResponse());

        // 复制按钮
        const copyBtn = document.getElementById('copyBtn');
        copyBtn.addEventListener('click', () => this.copyResponse());

        const faceMonitorBtn = document.getElementById('faceMonitorBtn');
        if (faceMonitorBtn) {
            faceMonitorBtn.addEventListener('click', () => this.toggleRealtimeFaceMonitor());
        }
    }

    async toggleRecording() {
        if (!this.isRecording) {
            await this.startRecording();
        } else {
            await this.stopRecording();
        }
    }

    async startRecording() {
        try {
            this.pendingFrameBlob = null;

            // 请求麦克风权限
            this.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            await this.ensureCameraStream();
            await this.setupAudioRecorder();
            this.isRecording = true;
            this.updateRecordingUI(true);
            this.updateStatus('正在录音...', 'recording');
            this.updateCameraStatus(this.cameraStream ? '摄像头已开启' : '仅麦克风模式');
             
        } catch (error) {
            console.error('无法访问麦克风:', error);
            alert('无法访问麦克风，请检查权限设置');
            // 如果无法访问麦克风，使用模拟模式
            this.simulateRecording();
        }
    }

    async stopRecording() {
        if (this.audioStream && this.isRecording) {
            this.pendingFrameBlob = await this.captureVideoFrame();
            const audioBlob = await this.finalizeAudioRecording();
            this.isRecording = false;
            this.updateRecordingUI(false);
            this.updateStatus('处理中...', 'processing');
            if (!this.realtimeFaceEnabled) {
                this.stopCameraStream();
            }
            this.processAudio(audioBlob, this.pendingFrameBlob);
        }
    }

    // 模拟录音功能（用于演示，无需真实麦克风）
    simulateRecording() {
        this.isRecording = true;
        this.updateRecordingUI(true);
        this.updateStatus('正在录音（模拟模式）...', 'recording');
        
        // 模拟录音3秒
        setTimeout(() => {
            this.isRecording = false;
            this.updateRecordingUI(false);
            this.updateStatus('处理中...', 'processing');
            this.processAudio(this.createMockAudioBlob());
        }, 3000);
    }

    createMockAudioBlob() {
        return new Blob(['mock audio content'], { type: 'audio/webm' });
    }

    async setupAudioRecorder() {
        this.recordedAudioBuffers = [];
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioContextClass();
        this.audioSourceNode = this.audioContext.createMediaStreamSource(this.audioStream);
        this.audioProcessorNode = this.audioContext.createScriptProcessor(4096, 1, 1);

        this.audioProcessorNode.onaudioprocess = (event) => {
            if (!this.isRecording) {
                return;
            }
            const channelData = event.inputBuffer.getChannelData(0);
            this.recordedAudioBuffers.push(new Float32Array(channelData));
        };

        this.audioSourceNode.connect(this.audioProcessorNode);
        this.audioProcessorNode.connect(this.audioContext.destination);
    }

    async finalizeAudioRecording() {
        const sourceSampleRate = this.audioContext?.sampleRate || 48000;
        const mergedBuffer = this.mergeAudioBuffers(this.recordedAudioBuffers);
        const downsampled = this.downsampleBuffer(mergedBuffer, sourceSampleRate, this.recordingSampleRate);
        const wavBlob = this.encodeWavBlob(downsampled, this.recordingSampleRate);
        await this.cleanupAudioRecorder();
        this.stopAudioStream();
        return wavBlob;
    }

    async cleanupAudioRecorder() {
        if (this.audioProcessorNode) {
            this.audioProcessorNode.disconnect();
            this.audioProcessorNode.onaudioprocess = null;
            this.audioProcessorNode = null;
        }
        if (this.audioSourceNode) {
            this.audioSourceNode.disconnect();
            this.audioSourceNode = null;
        }
        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }
    }

    mergeAudioBuffers(chunks) {
        const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
        const merged = new Float32Array(totalLength);
        let offset = 0;
        chunks.forEach((chunk) => {
            merged.set(chunk, offset);
            offset += chunk.length;
        });
        return merged;
    }

    downsampleBuffer(buffer, sourceRate, targetRate) {
        if (sourceRate === targetRate) {
            return buffer;
        }

        const ratio = sourceRate / targetRate;
        const newLength = Math.round(buffer.length / ratio);
        const result = new Float32Array(newLength);
        let offsetResult = 0;
        let offsetBuffer = 0;

        while (offsetResult < result.length) {
            const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
            let accum = 0;
            let count = 0;
            for (let index = offsetBuffer; index < nextOffsetBuffer && index < buffer.length; index += 1) {
                accum += buffer[index];
                count += 1;
            }
            result[offsetResult] = count > 0 ? accum / count : 0;
            offsetResult += 1;
            offsetBuffer = nextOffsetBuffer;
        }

        return result;
    }

    encodeWavBlob(samples, sampleRate) {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);

        this.writeWavString(view, 0, 'RIFF');
        view.setUint32(4, 36 + samples.length * 2, true);
        this.writeWavString(view, 8, 'WAVE');
        this.writeWavString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        this.writeWavString(view, 36, 'data');
        view.setUint32(40, samples.length * 2, true);

        let offset = 44;
        samples.forEach((sample) => {
            const clamped = Math.max(-1, Math.min(1, sample));
            view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
            offset += 2;
        });

        return new Blob([view], { type: 'audio/wav' });
    }

    writeWavString(view, offset, text) {
        for (let index = 0; index < text.length; index += 1) {
            view.setUint8(offset + index, text.charCodeAt(index));
        }
    }

    async ensureCameraStream() {
        if (this.cameraStream) {
            return;
        }

        try {
            this.cameraStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 360 } });
            const preview = document.getElementById('cameraPreview');
            const placeholder = document.getElementById('cameraPlaceholder');

            if (preview) {
                preview.srcObject = this.cameraStream;
                await preview.play().catch(() => {});
            }
            if (placeholder) {
                placeholder.classList.add('hidden');
            }

            this.updateCameraStatus('摄像头已开启');
        } catch (error) {
            console.warn('摄像头未启用，face 模态将降级:', error);
            this.cameraStream = null;
            this.updateCameraStatus('摄像头未授权');
        }
    }

    async toggleRealtimeFaceMonitor() {
        if (this.realtimeFaceEnabled) {
            this.disableRealtimeFaceMonitor();
            return;
        }

        await this.enableRealtimeFaceMonitor();
    }

    async enableRealtimeFaceMonitor() {
        const button = document.getElementById('faceMonitorBtn');
        await this.ensureCameraStream();
        if (!this.cameraStream) {
            return;
        }

        this.realtimeFaceEnabled = true;
        if (button) {
            button.textContent = '关闭实时表情识别';
            button.classList.add('active');
        }
        this.updateCameraStatus('实时识别中');
        this.runRealtimeFaceLoop(true);
    }

    disableRealtimeFaceMonitor() {
        const button = document.getElementById('faceMonitorBtn');
        this.realtimeFaceEnabled = false;
        this.faceEmotionHistory = [];
        if (this.faceLoopTimer) {
            clearTimeout(this.faceLoopTimer);
            this.faceLoopTimer = null;
        }
        if (button) {
            button.textContent = '开启实时表情识别';
            button.classList.remove('active');
        }
        if (!this.isRecording) {
            this.stopCameraStream();
        }
        this.updateCameraEmotionResult({
            available: false,
            emotion: '等待采样',
            evidence: ['已停止识别'],
            reliability: 0,
            raw_scores: {}
        });
    }

    async runRealtimeFaceLoop(runImmediately = false) {
        if (!this.realtimeFaceEnabled) {
            return;
        }

        if (runImmediately) {
            await this.refreshFaceEmotion();
        }

        this.faceLoopTimer = setTimeout(async () => {
            await this.refreshFaceEmotion();
            this.runRealtimeFaceLoop(false);
        }, 1200);
    }

    async refreshFaceEmotion() {
        if (!this.realtimeFaceEnabled || !this.cameraStream) {
            return;
        }

        const frameBlob = await this.captureVideoFrame();
        if (!frameBlob) {
            return;
        }

        try {
            const detectedFaceEmotion = await APIIntegration.analyzeFaceEmotion(frameBlob);
            const faceEmotion = this.getSmoothedFaceEmotion(detectedFaceEmotion);
            this.latestFaceEmotion = faceEmotion;
            this.renderFusionInsights(this.buildLiveModalities(faceEmotion), {
                provider: 'face-live',
                latency_ms: '--',
                audio_format: '--'
            });
            this.updateCameraEmotionResult(faceEmotion);

            if (!this.isRecording && faceEmotion.available !== false) {
                this.updateAvatarEmotion(faceEmotion.emotion);
                document.getElementById('emotionValue').textContent = `${faceEmotion.emotion} (${Math.round((faceEmotion.confidence || 0) * 100)}%)`;
            }
        } catch (error) {
            console.warn('实时表情识别刷新失败:', error);
            this.updateCameraEmotionResult({
                available: false,
                emotion: '识别失败',
                evidence: ['请稍后重试'],
                reliability: 0,
                raw_scores: {}
            });
        }
    }

    getSmoothedFaceEmotion(faceEmotion) {
        if (!faceEmotion || faceEmotion.available === false) {
            this.faceEmotionHistory = [];
            return faceEmotion;
        }

        this.faceEmotionHistory.push(faceEmotion);
        if (this.faceEmotionHistory.length > this.faceSmoothingWindow) {
            this.faceEmotionHistory.shift();
        }

        const mergedDistribution = {};
        let confidenceSum = 0;
        let reliabilitySum = 0;
        const evidence = [];
        const rawScores = {};

        this.faceEmotionHistory.forEach((item, index) => {
            const weight = index + 1;
            Object.entries(item.distribution || {}).forEach(([emotion, score]) => {
                mergedDistribution[emotion] = (mergedDistribution[emotion] || 0) + score * weight;
            });
            Object.entries(item.raw_scores || {}).forEach(([label, score]) => {
                rawScores[label] = (rawScores[label] || 0) + score * weight;
            });
            confidenceSum += (item.confidence || 0) * weight;
            reliabilitySum += (item.reliability || 0) * weight;
            (item.evidence || []).slice(0, 2).forEach((entry) => {
                if (!evidence.includes(entry)) {
                    evidence.push(entry);
                }
            });
        });

        const totalWeight = this.faceEmotionHistory.reduce((sum, _, index) => sum + index + 1, 0);
        Object.keys(mergedDistribution).forEach((emotion) => {
            mergedDistribution[emotion] = mergedDistribution[emotion] / totalWeight;
        });
        Object.keys(rawScores).forEach((label) => {
            rawScores[label] = rawScores[label] / totalWeight;
        });

        const smoothedEmotion = Object.entries(mergedDistribution)
            .sort((left, right) => right[1] - left[1])[0]?.[0] || faceEmotion.emotion;

        return {
            ...faceEmotion,
            emotion: smoothedEmotion,
            confidence: confidenceSum / totalWeight,
            reliability: reliabilitySum / totalWeight,
            distribution: mergedDistribution,
            raw_scores: rawScores,
            evidence: [...evidence.slice(0, 3), `smooth-window=${this.faceEmotionHistory.length}`]
        };
    }

    stopAudioStream() {
        if (!this.audioStream) {
            return;
        }

        this.audioStream.getTracks().forEach((track) => track.stop());
        this.audioStream = null;
    }

    stopCameraStream() {
        if (!this.cameraStream) {
            return;
        }

        this.cameraStream.getTracks().forEach((track) => track.stop());
        this.cameraStream = null;

        const preview = document.getElementById('cameraPreview');
        const placeholder = document.getElementById('cameraPlaceholder');
        if (preview) {
            preview.srcObject = null;
        }
        if (placeholder) {
            placeholder.classList.remove('hidden');
        }

        this.updateCameraStatus('待启用');
    }

    async captureVideoFrame() {
        const preview = document.getElementById('cameraPreview');
        const canvas = document.getElementById('frameCanvas');
        if (!preview || !canvas || !this.cameraStream || preview.videoWidth === 0 || preview.videoHeight === 0) {
            return null;
        }

        canvas.width = preview.videoWidth;
        canvas.height = preview.videoHeight;
        const context = canvas.getContext('2d');
        context.drawImage(preview, 0, 0, canvas.width, canvas.height);

        return await new Promise((resolve) => {
            canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.92);
        });
    }

    updateCameraStatus(text) {
        const cameraStatus = document.getElementById('cameraStatus');
        if (cameraStatus) {
            cameraStatus.textContent = text;
        }
    }

    updateRecordingUI(recording) {
        const recordBtn = document.getElementById('recordBtn');
        const waveAnimation = document.getElementById('waveAnimation');
        const recordText = recordBtn.querySelector('.record-text');
        
        if (recording) {
            recordBtn.classList.add('recording');
            recordText.textContent = '点击停止录音';
            waveAnimation.style.display = 'flex';
        } else {
            recordBtn.classList.remove('recording');
            recordText.textContent = '点击开始录音';
            waveAnimation.style.display = 'none';
        }
    }

    updateStatus(text, type = 'idle') {
        const statusText = document.getElementById('statusText');
        statusText.textContent = text;
        
        // 根据状态类型更新颜色
        const colors = {
            'idle': '#666',
            'recording': '#f5576c',
            'processing': '#667eea'
        };
        statusText.style.color = colors[type] || colors.idle;
    }

    async checkAPIStatus() {
        const apiStatus = document.getElementById('apiStatus');

        try {
            const healthUrl = `${window.APP_CONFIG.API_BASE_URL}${window.APP_CONFIG.ENDPOINTS.HEALTH}`;
            const response = await fetch(healthUrl);

            if (!response.ok) {
                throw new Error('Health check failed');
            }

            const data = await response.json();
            apiStatus.textContent = data.use_mock_services ? '已连接（Mock 模式）' : '已连接（真实接口）';
        } catch (error) {
            apiStatus.textContent = '未连接';
        }
    }

    async processAudio(audioBlob = null, frameBlob = null) {
        if (window.APP_CONFIG.USE_MOCK_DATA) {
            this.simulateProcessing();
            return;
        }

        const requestBlob = audioBlob || this.createMockAudioBlob();

        try {
            this.updateStatus('正在识别语音...', 'processing');
            this.updateSystemStatus('正在调用后端接口');

            const speechResult = await APIIntegration.recognizeSpeech(requestBlob, frameBlob);
            const transcription = speechResult.text || '未识别到有效文本';
            const emotionData = speechResult.emotion || {
                emotion: '平静',
                confidence: 0.5,
                tags: ['平静', '中性']
            };

            this.currentEmotionData = emotionData;
            this.displayTranscription(transcription);
            this.displayEmotionAnalysis(emotionData);
            this.renderFusionInsights(speechResult.modalities || this.buildFallbackModalities(emotionData), speechResult.meta || {});
            this.updateAvatarEmotion(emotionData.emotion);

            this.updateStatus('正在生成回应...', 'processing');

            const dialogueResult = await APIIntegration.generateEmotionalResponse(transcription, emotionData, this.conversationHistory);
            const responseText = dialogueResult.response;
            this.currentDialogueResult = dialogueResult;
            this.currentResponseText = responseText;
            this.appendConversationTurn(transcription, responseText, emotionData.emotion);
            this.currentTtsAudioUrl = '';
            this.displayResponse(responseText);
            this.prefetchTTS(responseText, dialogueResult.tts_emotion || emotionData.emotion);

            document.getElementById('playBtn').disabled = false;
            document.getElementById('copyBtn').disabled = false;

            this.updateStatus('处理完成', 'idle');
            this.updateSystemStatus('后端响应已生成');
        } catch (error) {
            console.error('后端接口调用失败，回退到模拟模式:', error);
            this.updateStatus('接口失败，切换演示模式', 'idle');
            this.updateSystemStatus('后端调用失败，已切换为本地演示');
            this.simulateProcessing();
        }
    }

    simulateProcessing() {
        // 模拟语音识别结果
        const mockTranscriptions = [
            "今天天气真好，心情也不错！",
            "最近工作压力有点大，感觉有点累...",
            "我想和你聊聊天，可以吗？",
            "今天遇到了一些不开心的事情",
            "谢谢你一直陪伴着我"
        ];
        
        const mockEmotions = [
            { emotion: "开心", confidence: 0.85, tags: ["快乐", "积极", "轻松"] },
            { emotion: "疲惫", confidence: 0.78, tags: ["压力", "疲惫", "需要安慰"] },
            { emotion: "平静", confidence: 0.72, tags: ["友好", "期待", "平静"] },
            { emotion: "难过", confidence: 0.82, tags: ["悲伤", "需要倾听", "情绪低落"] },
            { emotion: "感激", confidence: 0.88, tags: ["感谢", "温暖", "积极"] }
        ];
        
        const randomIndex = Math.floor(Math.random() * mockTranscriptions.length);
        const transcription = mockTranscriptions[randomIndex];
        const emotionData = mockEmotions[randomIndex];
        this.currentEmotionData = emotionData;
        const modalities = this.buildMockModalities(emotionData);
        
        // 显示识别结果
        this.displayTranscription(transcription);
        this.renderFusionInsights(modalities, {
            latency_ms: 680,
            provider: 'mock',
            audio_format: 'webm'
        });
        
        // 模拟API处理延迟
        setTimeout(() => {
            this.generateResponse(transcription, emotionData);
        }, 1500);
    }

    displayTranscription(text) {
        const transcriptionContent = document.getElementById('transcriptionContent');
        transcriptionContent.classList.add('typing');
        transcriptionContent.textContent = text;
        
        // 移除动画类以便下次可以重新触发
        setTimeout(() => {
            transcriptionContent.classList.remove('typing');
        }, 500);
    }

    buildMockModalities(emotionData) {
        return {
            text: {
                source: 'text',
                emotion: emotionData.emotion,
                confidence: Math.max(0.6, emotionData.confidence - 0.04),
                reliability: 0.74,
                evidence: [emotionData.tags[0] || '关键词触发'],
                available: true
            },
            speech: {
                source: 'speech',
                emotion: emotionData.emotion,
                confidence: emotionData.confidence,
                reliability: 0.7,
                evidence: [emotionData.tags[1] || '韵律代理特征'],
                available: true
            },
            face: {
                source: 'face',
                emotion: '平静',
                confidence: 0.2,
                reliability: 0,
                evidence: ['视频表情通道待接入'],
                raw_scores: { neutral: 0.82, happiness: 0.06, sadness: 0.04 },
                available: false
            },
            fusion: {
                emotion: emotionData.emotion,
                confidence: emotionData.confidence,
                strategy: 'reliability-aware late fusion',
                agreement_bonus: 0.08,
                top_candidates: [
                    { emotion: emotionData.emotion, score: emotionData.confidence },
                    { emotion: '平静', score: 1 - emotionData.confidence }
                ]
            }
        };
    }

    buildFallbackModalities(emotionData) {
        const modalities = this.buildMockModalities(emotionData);
        if (this.latestFaceEmotion) {
            modalities.face = this.latestFaceEmotion;
        }
        return modalities;
    }

    buildLiveModalities(faceEmotion) {
        return {
            text: {
                source: 'text',
                emotion: '平静',
                confidence: 0.18,
                reliability: 0,
                evidence: ['等待语音输入'],
                available: false
            },
            speech: {
                source: 'speech',
                emotion: '平静',
                confidence: 0.18,
                reliability: 0,
                evidence: ['等待语音输入'],
                available: false
            },
            face: faceEmotion,
            fusion: {
                emotion: faceEmotion.emotion,
                confidence: faceEmotion.confidence,
                strategy: 'live-face-monitor',
                agreement_bonus: 0,
                top_candidates: Object.entries(faceEmotion.distribution || {})
                    .sort((left, right) => right[1] - left[1])
                    .slice(0, 3)
                    .map(([emotion, score]) => ({ emotion, score }))
            }
        };
    }

    async prefetchTTS(text, emotion) {
        if (!text) {
            return;
        }

        this.updateSystemStatus('文本已生成，正在准备语音');
        this.pendingTtsPromise = APIIntegration.textToSpeech(text, emotion)
            .then((audioUrl) => {
                this.currentTtsAudioUrl = audioUrl || '';
                this.updateSystemStatus('文本与语音均已准备');
                return audioUrl;
            })
            .catch((error) => {
                console.warn('预生成语音失败，将回退浏览器朗读:', error);
                this.currentTtsAudioUrl = '';
                return '';
            });
        return this.pendingTtsPromise;
    }

    appendConversationTurn(userText, assistantText, emotion) {
        this.conversationHistory.push({
            user: userText,
            assistant: assistantText,
            emotion: emotion
        });

        if (this.conversationHistory.length > 4) {
            this.conversationHistory.shift();
        }
    }

    renderFusionInsights(modalities, meta = {}) {
        const fusionGrid = document.getElementById('fusionGrid');
        const fusionMeta = document.getElementById('fusionMeta');

        if (!fusionGrid || !modalities) {
            return;
        }

        const orderedKeys = ['text', 'speech', 'face', 'fusion'];
        fusionGrid.innerHTML = orderedKeys.map((key) => this.buildFusionCard(key, modalities[key] || null)).join('');

        if (modalities.face) {
            this.updateCameraEmotionResult(modalities.face);
        }

        const fusionStrategy = modalities.fusion?.strategy || 'reliability-aware late fusion';
        const latency = meta.latency_ms ?? '--';
        const provider = meta.provider || 'mock';
        const audioFormat = meta.audio_format || '--';
        fusionMeta.innerHTML = [
            `<span>融合策略：${fusionStrategy}</span>`,
            `<span>时延：${latency} ms</span>`,
            `<span>ASR 来源：${provider}</span>`,
            `<span>音频格式：${audioFormat}</span>`
        ].join('');
    }

    buildFusionCard(key, data) {
        const titleMap = {
            text: '文本',
            speech: '语音',
            face: '表情',
            fusion: '融合'
        };

        if (!data) {
            return `
                <article class="fusion-card pending">
                    <span class="fusion-source">${titleMap[key]}</span>
                    <strong>暂无结果</strong>
                    <p>等待模块输出。</p>
                </article>
            `;
        }

        if (key === 'fusion') {
            const topCandidates = (data.top_candidates || []).map((item) => `<span class="fusion-chip">${item.emotion} ${Math.round(item.score * 100)}%</span>`).join('');
            return `
                <article class="fusion-card focus">
                    <span class="fusion-source">${titleMap[key]}</span>
                    <strong>${data.emotion} (${Math.round((data.confidence || 0) * 100)}%)</strong>
                    <p>一致性增强 + 可靠度加权的决策级融合结果。</p>
                    <div class="fusion-chip-row">${topCandidates || '<span class="fusion-chip">等待候选</span>'}</div>
                </article>
            `;
        }

        const statusText = data.available === false ? '待接入' : `${data.emotion} (${Math.round((data.confidence || 0) * 100)}%)`;
        const evidence = (data.evidence || []).slice(0, 2).map((item) => `<span class="fusion-chip">${item}</span>`).join('');
        const reliabilityText = data.available === false ? '可靠度 0%' : `可靠度 ${Math.round((data.reliability || 0) * 100)}%`;
        const rawTop = this.getTopRawScores(data.raw_scores);
        const rawText = rawTop.length > 0 ? `原始输出：${rawTop.join(' / ')}` : '';

        return `
            <article class="fusion-card ${data.available === false ? 'pending' : ''}">
                <span class="fusion-source">${titleMap[key]}</span>
                <strong>${statusText}</strong>
                <p>${reliabilityText}</p>
                ${rawText ? `<p>${rawText}</p>` : ''}
                <div class="fusion-chip-row">${evidence || '<span class="fusion-chip">暂无证据</span>'}</div>
            </article>
        `;
    }

    getTopRawScores(rawScores) {
        if (!rawScores) {
            return [];
        }

        const labelMap = {
            happiness: '开心',
            neutral: '平静',
            sadness: '难过',
            anger: '愤怒',
            fear: '紧张',
            disgust: '厌恶',
            surprise: '惊讶',
            contempt: '轻蔑',
            neu: '平静',
            hap: '开心',
            ang: '愤怒',
            sad: '难过'
        };

        return Object.entries(rawScores)
            .sort((left, right) => right[1] - left[1])
            .slice(0, 3)
            .map(([label, score]) => `${labelMap[label] || label} ${Math.round(score * 100)}%`);
    }

    async generateResponse(transcription, emotionData) {
        // TODO: 调用大模型API
        // const response = await fetch('/api/generate-response', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({
        //         text: transcription,
        //         emotion: emotionData
        //     })
        // });
        // const data = await response.json();
        
        // 当前为模拟响应
        const mockResponses = {
            "开心": [
                "太好了！听到你心情不错，我也为你感到高兴呢！😊 今天有什么特别开心的事情想和我分享吗？",
                "真棒！好心情是会传染的，你的快乐也让我感到温暖。希望这份好心情能一直陪伴着你！",
                "太好了！看到你这么开心，我也忍不住想笑呢。让我们一起享受这美好的时刻吧！"
            ],
            "疲惫": [
                "我理解你的感受，工作压力确实不容易。要不要先休息一下，或者和我聊聊，也许能让你感觉好一些？💙",
                "辛苦了，我知道你一直在努力。记得要照顾好自己，适当的休息也很重要。我会一直在这里陪伴你的。",
                "感受到你的疲惫了，这确实不容易。要不要先放松一下，我们可以慢慢聊，不用着急。"
            ],
            "平静": [
                "当然可以！我很乐意和你聊天。你想聊什么呢？我会认真倾听的。😊",
                "很高兴你想和我聊天！我在这里，随时准备倾听你的心声。",
                "当然可以聊天！我很期待我们的对话，你想从什么话题开始呢？"
            ],
            "难过": [
                "我感受到了你的难过，这一定很不容易。如果你愿意的话，可以和我详细说说，我会认真倾听的。💙",
                "听到你遇到不开心的事情，我也为你感到心疼。记住，你并不孤单，我会一直陪伴在你身边。",
                "我理解你的感受，难过的时候确实需要有人陪伴。如果你想说，我会认真听；如果不想说，我也会默默陪伴你。"
            ],
            "感激": [
                "听到你这么说，我也很感动。能够陪伴你，对我来说也是一件很幸福的事情。💙",
                "谢谢你！你的感谢让我感到温暖。能够成为你的陪伴，是我最大的快乐。",
                "我也要谢谢你，能够和你交流让我感到很有意义。希望我们能一直这样互相陪伴下去。"
            ]
        };
        
        const responses = mockResponses[emotionData.emotion] || mockResponses["平静"];
        const responseText = responses[Math.floor(Math.random() * responses.length)];
        this.currentDialogueResult = {
            response: responseText,
            emotion_style: emotionData.emotion,
            response_emotion_target: emotionData.emotion,
            empathy_strategy: 'mock',
            tts_emotion: emotionData.emotion
        };
        this.currentResponseText = responseText;
        this.appendConversationTurn(transcription, responseText, emotionData.emotion);
        this.currentTtsAudioUrl = '';
        
        // 显示AI回答
        this.displayResponse(responseText);
        this.prefetchTTS(responseText, this.currentDialogueResult.tts_emotion);
        
        // 显示情绪分析
        this.displayEmotionAnalysis(emotionData);
        
        // 更新虚拟形象情绪
        this.updateAvatarEmotion(emotionData.emotion);
        
        // 启用按钮
        document.getElementById('playBtn').disabled = false;
        document.getElementById('copyBtn').disabled = false;
        
        this.updateStatus('处理完成', 'idle');
        this.updateSystemStatus('响应已生成');
    }

    displayResponse(text) {
        const responseContent = document.getElementById('responseContent');
        const responseBox = responseContent.closest('.response-box');
        
        // 添加内容标记以触发动画
        responseBox.classList.add('has-content');
        
        // 打字机效果（可选）
        this.typeWriter(responseContent, text, 30);
    }
    
    typeWriter(element, text, speed = 30) {
        element.innerHTML = '';
        let i = 0;
        const timer = setInterval(() => {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
            } else {
                clearInterval(timer);
            }
        }, speed);
    }

    displayEmotionAnalysis(emotionData) {
        const emotionTags = document.getElementById('emotionTags');
        const emotionValue = document.getElementById('emotionValue');
        
        // 添加数字动画效果
        const confidence = emotionData.confidence * 100;
        this.animateNumber(emotionValue, 0, confidence, 1000, (value) => {
            emotionValue.textContent = `${emotionData.emotion} (${value.toFixed(0)}%)`;
        });
        
        // 清空并重新添加标签以触发动画
        emotionTags.innerHTML = '';
        emotionData.tags.forEach((tag, index) => {
            setTimeout(() => {
                const tagElement = document.createElement('span');
                tagElement.className = 'tag';
                tagElement.textContent = tag;
                emotionTags.appendChild(tagElement);
            }, index * 100);
        });
    }
    
    animateNumber(element, start, end, duration, callback) {
        const startTime = performance.now();
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = start + (end - start) * this.easeOutCubic(progress);
            callback(current);
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        requestAnimationFrame(animate);
    }
    
    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    updateAvatarEmotion(emotion) {
        const avatarDisplay = document.getElementById('avatarDisplay');
        document.body.setAttribute('data-emotion', emotion);
        const emotionMap = {
            "开心": { 
                bg: "radial-gradient(circle at top, #fff6dc, #f0d49a 74%)", 
                expression: "happy",
                class: "happy"
            },
            "疲惫": { 
                bg: "radial-gradient(circle at top, #eef0e2, #bcc5a3 74%)", 
                expression: "tired",
                class: "tired"
            },
            "平静": { 
                bg: "radial-gradient(circle at top, #ecfaf8, #bfdad6 74%)", 
                expression: "calm",
                class: "calm"
            },
            "难过": { 
                bg: "radial-gradient(circle at top, #eef6fb, #c8d9e4 74%)", 
                expression: "sad",
                class: "sad"
            },
            "感激": { 
                bg: "radial-gradient(circle at top, #fff0e7, #efc6af 74%)", 
                expression: "grateful",
                class: "grateful"
            }
        };
        
        const emotionStyle = emotionMap[emotion] || emotionMap["平静"];
        
        // 移除所有情绪类
        avatarDisplay.classList.remove('happy', 'sad', 'tired', 'calm', 'grateful');
        
        // 添加新情绪类
        if (emotionStyle.class) {
            avatarDisplay.classList.add(emotionStyle.class);
        }
        
        // 平滑过渡背景色
        avatarDisplay.style.transition = 'background 0.5s ease';
        avatarDisplay.style.background = emotionStyle.bg;
        
        // 添加表情变化动画
        avatarDisplay.style.animation = 'none';
        setTimeout(() => {
            avatarDisplay.style.animation = 'bounce 0.5s ease';
        }, 10);
    }

    playResponse() {
        if (!this.currentResponseText) {
            return;
        }

        const playBtn = document.getElementById('playBtn');
        const originalText = playBtn.innerHTML;
        playBtn.innerHTML = '<span>⏸️</span> 播放中...';
        playBtn.disabled = true;

        const finishPlayback = () => {
            playBtn.innerHTML = originalText;
            playBtn.disabled = false;
        };

        if (window.APP_CONFIG.USE_MOCK_DATA) {
            this.speakWithBrowser(this.currentResponseText);
            setTimeout(finishPlayback, 1000);
            return;
        }

        const pendingAudio = this.pendingTtsPromise || Promise.resolve(this.currentTtsAudioUrl);
        pendingAudio
            .then((audioUrl) => {
                if (!audioUrl || audioUrl.includes('example.com')) {
                    this.handleTtsFailure(playBtn, originalText);
                    return;
                }

                const audio = new Audio(audioUrl);
                audio.addEventListener('ended', finishPlayback, { once: true });
                audio.addEventListener('error', () => {
                    this.handleTtsFailure(playBtn, originalText, '语音播放失败，请重试');
                }, { once: true });
                audio.play().catch(() => {
                    this.handleTtsFailure(playBtn, originalText, '语音播放失败，请重试');
                });
            })
            .catch(() => {
                this.handleTtsFailure(playBtn, originalText);
            });
    }

    speakWithBrowser(text) {
        if (!('speechSynthesis' in window)) {
            return;
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'zh-CN';
        utterance.rate = 1;
        utterance.pitch = 1;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    copyResponse() {
        const responseText = document.getElementById('responseContent').textContent;
        navigator.clipboard.writeText(responseText).then(() => {
            const copyBtn = document.getElementById('copyBtn');
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '<span>✅</span> 已复制';
            setTimeout(() => {
                copyBtn.innerHTML = originalText;
            }, 2000);
        });
    }

    handleTtsFailure(playBtn, originalText, reason = '语音生成失败，请稍后重试') {
        this.updateSystemStatus(reason);
        playBtn.innerHTML = originalText;
        playBtn.disabled = false;
    }

    updateCameraEmotionResult(faceEmotion) {
        const result = document.getElementById('cameraEmotionResult');
        if (!result) {
            return;
        }

        if (!faceEmotion) {
            result.innerHTML = `
                <article class="fusion-card pending">
                    <span class="fusion-source">表情</span>
                    <strong>等待采样</strong>
                    <p>启用实时表情识别后，会在这里同步显示表情分析结果。</p>
                </article>
            `;
            return;
        }

        result.innerHTML = this.buildFusionCard('face', faceEmotion);
    }

    updateSystemStatus(status) {
        document.getElementById('systemStatus').textContent = status;
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new VirtualCompanionDemo();
});

// API集成示例函数（供后续使用）
class APIIntegration {
    /**
     * 发送音频到语音识别API
     * @param {Blob} audioBlob - 录音音频数据
     * @returns {Promise<Object>} 识别结果和情绪分析
     */
    static async recognizeSpeech(audioBlob, frameBlob = null) {
        const formData = new FormData();
        const mimeType = audioBlob.type || 'audio/webm';
        const extension = APIIntegration.getAudioExtension(mimeType);
        formData.append('audio', audioBlob, `recording.${extension}`);

        if (frameBlob) {
            formData.append('frame', frameBlob, 'frame.jpg');
        }

        const apiUrl = `${window.APP_CONFIG.API_BASE_URL}${window.APP_CONFIG.ENDPOINTS.SPEECH_RECOGNITION}`;
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('语音识别失败');
        }
        
        return await response.json();
    }

    static getAudioExtension(mimeType) {
        const formatMap = {
            'audio/wav': 'wav',
            'audio/x-wav': 'wav',
            'audio/mpeg': 'mp3',
            'audio/mp3': 'mp3',
            'audio/mp4': 'mp4',
            'audio/m4a': 'm4a',
            'audio/aac': 'aac',
            'audio/ogg': 'ogg',
            'audio/opus': 'opus',
            'audio/webm': 'webm'
        };

        return formatMap[mimeType] || 'webm';
    }

    static async analyzeFaceEmotion(frameBlob) {
        const apiUrl = `${window.APP_CONFIG.API_BASE_URL}${window.APP_CONFIG.ENDPOINTS.EMOTION_FACE}`;
        const formData = new FormData();
        formData.append('frame', frameBlob, 'frame.jpg');

        const response = await fetch(apiUrl, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('表情识别失败');
        }

        return await response.json();
    }

    /**
     * 调用大模型生成情感化回答
     * @param {string} text - 用户输入的文本
     * @param {Object} emotionData - 情绪分析数据
     * @returns {Promise<Object>} AI生成的回答对象
     */
    static async generateEmotionalResponse(text, emotionData, conversationHistory = []) {
        const apiUrl = `${window.APP_CONFIG.API_BASE_URL}${window.APP_CONFIG.ENDPOINTS.GENERATE_RESPONSE}`;

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                emotion: emotionData.emotion,
                emotion_confidence: emotionData.confidence,
                context: emotionData.tags,
                recent_dialogue: conversationHistory
            })
        });
        
        if (!response.ok) {
            throw new Error('生成回答失败');
        }
        
        return await response.json();
    }

    /**
     * 文本转语音
     * @param {string} text - 要转换的文本
     * @returns {Promise<string>} 音频URL
     */
    static async textToSpeech(text, emotion = 'neutral') {
        const apiUrl = `${window.APP_CONFIG.API_BASE_URL}${window.APP_CONFIG.ENDPOINTS.TEXT_TO_SPEECH}`;

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                emotion: emotion
            })
        });
        
        if (!response.ok) {
            throw new Error('语音合成失败');
        }
        
        const data = await response.json();
        return data.audio_url;
    }
}

// 导出供全局使用
window.APIIntegration = APIIntegration;
