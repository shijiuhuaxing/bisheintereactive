import base64
import hashlib
import threading
import uuid
import wave
from pathlib import Path

import dashscope
from dashscope.audio.qwen_tts_realtime import AudioFormat, QwenTtsRealtime, QwenTtsRealtimeCallback

from ..schemas.speech import tts_result


OUTPUT_DIR = Path(__file__).resolve().parents[3] / 'outputs' / 'audios'
TTS_CACHE = {}

EMOTION_INSTRUCTIONS = {
    '开心': '用被用户好心情感染后的开心语气说，明亮、轻快、自然带笑意，语速略快。',
    '难过': '用陪伴式难过和心疼的语气说，温柔、低缓、安抚，情绪真诚但不过度夸张。',
    '疲惫': '用轻柔、放缓、像在托住对方的语气说，安稳、低刺激、带安慰感。',
    '感激': '用温暖、真诚、被触动的语气说，语调柔和，保持亲切感。',
    '平静': '用自然、稳定、开放的陪伴语气说，发音清晰，适合日常交流。',
}


class _RealtimeCollectCallback(QwenTtsRealtimeCallback):
    def __init__(self):
        super().__init__()
        self.audio_chunks = []
        self.complete_event = threading.Event()
        self.error = None

    def on_open(self) -> None:
        return None

    def on_close(self, close_status_code, close_msg) -> None:
        if close_status_code not in (1000, None) and self.error is None:
            self.error = f'Qwen3-TTS 连接关闭: code={close_status_code}, msg={close_msg}'
        self.complete_event.set()

    def on_event(self, response: dict) -> None:
        try:
            event_type = response.get('type', '')
            if event_type == 'response.audio.delta':
                self.audio_chunks.append(base64.b64decode(response['delta']))
            elif event_type == 'error':
                self.error = str(response.get('error', {}))
                self.complete_event.set()
            elif event_type in ('response.done', 'session.finished'):
                self.complete_event.set()
        except Exception as exc:  # pragma: no cover
            self.error = str(exc)
            self.complete_event.set()

    def wait_for_completion(self, timeout: float = 45.0) -> bytes:
        if not self.complete_event.wait(timeout):
            raise TimeoutError('等待 Qwen3-TTS 返回音频超时')
        if self.error:
            raise RuntimeError(self.error)
        if not self.audio_chunks:
            raise RuntimeError('Qwen3-TTS 未返回音频数据')
        return b''.join(self.audio_chunks)


def synthesize_speech(text: str, emotion: str, settings, base_url: str) -> dict:
    if not text.strip():
        return tts_result('', '文本为空，无法合成语音', provider='none')

    provider = (settings.tts_provider or 'mock').lower()
    if settings.use_mock_services or provider == 'mock':
        return build_mock_tts_result(text)

    if provider == 'qwen_dashscope':
        return synthesize_with_qwen_dashscope(text, emotion, settings, base_url)

    return tts_result('', f'未支持的 TTS provider: {provider}', provider=provider)


def build_mock_tts_result(text: str) -> dict:
    message = '当前仍为 mock TTS。前端会自动退回浏览器朗读。'
    return tts_result('http://example.com/audio/placeholder.mp3', message, provider='mock', meta={'text_length': len(text)})


def synthesize_with_qwen_dashscope(text: str, emotion: str, settings, base_url: str) -> dict:
    if not settings.dashscope_api_key:
        return tts_result('', '未配置 DASHSCOPE_API_KEY，无法调用 Qwen3-TTS。', provider='qwen_dashscope')

    dashscope.api_key = settings.dashscope_api_key

    instruction = EMOTION_INSTRUCTIONS.get(emotion, EMOTION_INSTRUCTIONS['平静'])
    cache_key = build_tts_cache_key(text, emotion, settings.dashscope_tts_model, settings.dashscope_tts_voice, instruction)

    cached_path = TTS_CACHE.get(cache_key)
    if cached_path and cached_path.exists():
        audio_url = f"{base_url}/api/tts/files/{cached_path.name}"
        return tts_result(
            audio_url,
            'Qwen3-TTS 命中缓存',
            provider='qwen_dashscope',
            meta={
                'voice': settings.dashscope_tts_voice,
                'model': settings.dashscope_tts_model,
                'emotion': emotion,
                'cached': True,
            },
        )

    last_error = None
    for attempt in range(2):
        callback = _RealtimeCollectCallback()
        client = QwenTtsRealtime(
            model=settings.dashscope_tts_model,
            callback=callback,
            url=settings.dashscope_tts_url,
        )

        try:
            client.connect()
            client.update_session(
                voice=settings.dashscope_tts_voice,
                response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
                instructions=instruction,
                optimize_instructions=True,
                mode='server_commit',
            )
            client.append_text(text)
            client.finish()
            pcm_audio = callback.wait_for_completion(timeout=25.0)
            audio_path = save_pcm_as_wav(pcm_audio, file_stem=cache_key)
            TTS_CACHE[cache_key] = audio_path
            break
        except Exception as exc:
            last_error = exc
            audio_path = None
        finally:
            try:
                client.close()
            except Exception:
                pass

    if audio_path is None:
        return tts_result('', f'Qwen3-TTS 调用失败: {last_error}', provider='qwen_dashscope')

    audio_url = f"{base_url}/api/tts/files/{audio_path.name}"
    return tts_result(
        audio_url,
        'Qwen3-TTS 合成成功',
        provider='qwen_dashscope',
        meta={
            'voice': settings.dashscope_tts_voice,
            'model': settings.dashscope_tts_model,
            'emotion': emotion,
            'cached': False,
        },
    )


def save_pcm_as_wav(audio_bytes: bytes, sample_rate: int = 24000, file_stem: str | None = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f'{file_stem}.wav' if file_stem else f'tts_{uuid.uuid4().hex}.wav'
    file_path = OUTPUT_DIR / file_name
    with wave.open(str(file_path), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
    return file_path


def build_tts_cache_key(text: str, emotion: str, model: str, voice: str, instruction: str) -> str:
    payload = f'{text}|{emotion}|{model}|{voice}|{instruction}'.encode('utf-8')
    return f'tts_{hashlib.md5(payload).hexdigest()}'
