import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / '.env', override=True)


@dataclass
class Settings:
    app_host: str = os.getenv('APP_HOST', '0.0.0.0')
    app_port: int = int(os.getenv('APP_PORT', '5000'))
    app_debug: bool = os.getenv('APP_DEBUG', 'true').lower() == 'true'
    use_mock_services: bool = os.getenv('USE_MOCK_SERVICES', 'true').lower() == 'true'
    asr_provider: str = os.getenv('ASR_PROVIDER', 'mock')
    text_emotion_provider: str = os.getenv('TEXT_EMOTION_PROVIDER', 'rules')
    text_emotion_model: str = os.getenv('TEXT_EMOTION_MODEL', 'qwen-turbo')
    speech_emotion_provider: str = os.getenv('SPEECH_EMOTION_PROVIDER', 'wav2vec2_superb')
    speech_emotion_model: str = os.getenv('SPEECH_EMOTION_MODEL', 'superb/wav2vec2-base-superb-er')
    dashscope_api_key: str = os.getenv('DASHSCOPE_API_KEY', '')
    dashscope_asr_model: str = os.getenv('DASHSCOPE_ASR_MODEL', 'paraformer-realtime-v2')
    llm_provider: str = os.getenv('LLM_PROVIDER', 'qwen_dashscope')
    llm_model: str = os.getenv('LLM_MODEL', 'qwen-turbo')
    tts_provider: str = os.getenv('TTS_PROVIDER', 'mock')
    dashscope_tts_model: str = os.getenv('DASHSCOPE_TTS_MODEL', 'qwen3-tts-instruct-flash-realtime')
    dashscope_tts_voice: str = os.getenv('DASHSCOPE_TTS_VOICE', 'Cherry')
    dashscope_tts_url: str = os.getenv('DASHSCOPE_TTS_URL', 'wss://dashscope.aliyuncs.com/api-ws/v1/realtime')
    llm_api_key: str = os.getenv('LLM_API_KEY', '')
    tts_api_key: str = os.getenv('TTS_API_KEY', '')
    cors_origins: str = os.getenv('CORS_ORIGINS', '*')


def get_settings() -> Settings:
    return Settings()
