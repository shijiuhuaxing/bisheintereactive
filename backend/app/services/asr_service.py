import os
import tempfile
import wave
from pathlib import Path

try:
    import dashscope
    from dashscope.audio.asr import Recognition, RecognitionCallback
except ImportError:  # pragma: no cover
    dashscope = None
    Recognition = None
    RecognitionCallback = None


MOCK_TRANSCRIPT = '我想和你聊聊天。'

MIME_EXTENSION_MAP = {
    'audio/wav': 'wav',
    'audio/x-wav': 'wav',
    'audio/mpeg': 'mp3',
    'audio/mp3': 'mp3',
    'audio/mp4': 'mp4',
    'audio/m4a': 'm4a',
    'audio/aac': 'aac',
    'audio/ogg': 'ogg',
    'audio/opus': 'opus',
    'audio/webm': 'webm',
}


class _NoopRecognitionCallback(RecognitionCallback):
    pass


def recognize_audio(file_storage, settings) -> dict:
    provider = getattr(settings, 'asr_provider', 'mock').lower()
    if settings.use_mock_services or provider == 'mock' or not settings.dashscope_api_key or dashscope is None or Recognition is None:
        return {
            'text': MOCK_TRANSCRIPT,
            'audio_path': None,
            'provider': 'mock',
            'format': 'wav',
        }

    dashscope.api_key = settings.dashscope_api_key

    source_format = detect_audio_format(file_storage)
    file_storage.stream.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{source_format}') as tmp_file:
        file_storage.save(tmp_file.name)
        tmp_path = tmp_file.name

    try:
        sample_rate = detect_sample_rate(tmp_path, source_format)
        recognition = Recognition(
            model=settings.dashscope_asr_model,
            callback=_NoopRecognitionCallback(),
            format=source_format,
            sample_rate=sample_rate,
        )
        result = recognition.call(tmp_path)

        if result.status_code != 200:
            raise RuntimeError(result.message)

        sentence = extract_sentence(result)
        return {
            'text': sentence,
            'audio_path': tmp_path,
            'provider': 'dashscope',
            'format': source_format,
        }
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise RuntimeError(build_asr_error_message(source_format, exc)) from exc


def detect_audio_format(file_storage) -> str:
    filename = (file_storage.filename or '').strip()
    if filename:
        suffix = Path(filename).suffix.lower().lstrip('.')
        if suffix:
            return normalize_audio_format(suffix)

    mimetype = (file_storage.mimetype or '').split(';', 1)[0].strip().lower()
    if mimetype in MIME_EXTENSION_MAP:
        return MIME_EXTENSION_MAP[mimetype]

    return 'wav'


def normalize_audio_format(audio_format: str) -> str:
    aliases = {
        'wave': 'wav',
        'x-wav': 'wav',
        'mpeg': 'mp3',
        'oga': 'ogg',
    }
    return aliases.get(audio_format, audio_format)


def detect_sample_rate(audio_path: str, source_format: str) -> int:
    if source_format == 'wav':
        with wave.open(audio_path, 'rb') as wav_file:
            return wav_file.getframerate()
    return 16000


def extract_sentence(result) -> str:
    output = getattr(result, 'output', None)
    if output is None:
        return ''

    if isinstance(output, dict):
        sentence = output.get('sentence', '')
        if isinstance(sentence, list):
            texts = [item.get('text', '') for item in sentence if isinstance(item, dict)]
            return ''.join(texts).strip()
        return sentence

    if hasattr(output, 'sentence'):
        sentence = output.sentence or ''
        if isinstance(sentence, list):
            texts = [item.get('text', '') for item in sentence if isinstance(item, dict)]
            return ''.join(texts).strip()
        return sentence

    return ''


def build_asr_error_message(source_format: str, exc: Exception) -> str:
    detail = str(exc)
    return f'DashScope ASR 调用失败，音频格式为 {source_format}。原始错误: {detail}'


def cleanup_audio_path(audio_path: str | None) -> None:
    if audio_path and os.path.exists(audio_path):
        os.unlink(audio_path)
