window.APP_CONFIG = {
    API_BASE_URL: 'http://localhost:5000',
    REALTIME_WS_URL: 'ws://127.0.0.1:8001/ws/realtime',
    ENABLE_REALTIME_SESSION: true,
    USE_MOCK_DATA: false,
    ENDPOINTS: {
        HEALTH: '/api/health',
        SPEECH_RECOGNITION: '/api/speech-recognition',
        EMOTION_FACE: '/api/emotion/face',
        GENERATE_RESPONSE: '/api/generate-response',
        TEXT_TO_SPEECH: '/api/text-to-speech'
    }
};
