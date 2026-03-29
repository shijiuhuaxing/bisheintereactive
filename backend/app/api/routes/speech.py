from flask import Blueprint, current_app, jsonify, request
from time import perf_counter

from ...schemas.speech import speech_result
from ...services.asr_service import cleanup_audio_path, recognize_audio
from ...services.emotion.face_emotion import analyze_face_emotion
from ...services.emotion.speech_emotion import analyze_speech_emotion
from ...services.emotion.text_emotion import analyze_text_emotion
from ...services.fusion_service import fuse_emotions

speech_bp = Blueprint('speech', __name__)

MOCK_NEUTRAL_PRIOR = {
    '开心': 0.14,
    '难过': 0.12,
    '疲惫': 0.12,
    '感激': 0.12,
    '平静': 0.5,
}


@speech_bp.post('/api/speech/recognize')
@speech_bp.post('/api/speech-recognition')
def recognize_speech_route():
    start_time = perf_counter()

    if 'audio' not in request.files:
        return jsonify({'error': '没有上传音频文件'}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    settings = current_app.config['SETTINGS']
    try:
        result = recognize_audio(audio_file, settings)
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 500

    recognized_text = result['text']
    audio_path = result.get('audio_path')

    try:
        text_emotion = analyze_text_emotion(recognized_text, settings)
        speech_emotion = analyze_speech_emotion(recognized_text, audio_path, settings)
        frame_file = request.files.get('frame')
        face_emotion = analyze_face_emotion(frame_file)

        if result.get('provider') == 'mock':
            face_available = bool(face_emotion.get('available', False))
            text_emotion = dampen_mock_modality(text_emotion, face_available)
            speech_emotion = dampen_mock_modality(speech_emotion, face_available)

        fused_emotion = fuse_emotions([text_emotion, speech_emotion, face_emotion])

        elapsed_ms = round((perf_counter() - start_time) * 1000, 1)
        modalities = {
            'text': text_emotion,
            'speech': speech_emotion,
            'face': face_emotion,
            'fusion': fused_emotion,
        }
        meta = {
            'latency_ms': elapsed_ms,
            'provider': result.get('provider', 'mock'),
            'audio_format': result.get('format', 'unknown'),
        }

        return jsonify(speech_result(recognized_text, fused_emotion, modalities=modalities, meta=meta))
    finally:
        cleanup_audio_path(audio_path)


def dampen_mock_modality(item: dict, face_available: bool) -> dict:
    adjusted = dict(item)
    current_distribution = item.get('distribution') or MOCK_NEUTRAL_PRIOR
    current_ratio = 0.25 if face_available else 0.4
    neutral_ratio = 1 - current_ratio

    mixed_distribution = {
        emotion: current_distribution.get(emotion, 0.0) * current_ratio + MOCK_NEUTRAL_PRIOR[emotion] * neutral_ratio
        for emotion in MOCK_NEUTRAL_PRIOR
    }

    adjusted_emotion = max(mixed_distribution, key=mixed_distribution.get)
    adjusted['emotion'] = adjusted_emotion
    adjusted['distribution'] = mixed_distribution
    adjusted['confidence'] = round(min(float(item.get('confidence', 0.0)), 0.28 if face_available else 0.4), 2)
    adjusted['reliability'] = round(0.08 if face_available else 0.18, 2)
    adjusted['tags'] = ['mock-asr', '低可信语义'] if face_available else ['mock-asr', '待真实语音接入']
    adjusted['evidence'] = list(item.get('evidence', [])) + ['mock-asr-low-trust']
    return adjusted
