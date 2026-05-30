from time import perf_counter

from flask import Blueprint, current_app, jsonify, request

from ...schemas.speech import speech_result
from ...services.asr_service import cleanup_audio_path, recognize_audio
from ...services.emotion.face_emotion import analyze_face_emotion
from ...services.emotion.speech_emotion import analyze_speech_emotion
from ...services.emotion.text_emotion import analyze_text_emotion
from ...services.fusion_service import fuse_emotions
from ...services.llm_service import generate_emotional_response


conversation_bp = Blueprint('conversation', __name__)


@conversation_bp.post('/api/conversation/turn')
def conversation_turn_route():
    start_time = perf_counter()
    if 'audio' not in request.files:
        return jsonify({'error': '没有上传音频文件'}), 400

    settings = current_app.config['SETTINGS']
    audio_file = request.files['audio']
    frame_file = request.files.get('frame')
    recent_dialogue = parse_recent_dialogue(request.form.get('recent_dialogue', ''))
    previous_fusion = parse_previous_fusion(request.form.get('previous_fusion', ''))

    try:
        asr_result = recognize_audio(audio_file, settings)
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 500

    recognized_text = asr_result['text']
    audio_path = asr_result.get('audio_path')

    try:
        text_emotion = analyze_text_emotion(recognized_text, settings)
        speech_emotion = analyze_speech_emotion(recognized_text, audio_path, settings)
        face_emotion = analyze_face_emotion(frame_file)
        temporal_context = {
            'recent_dialogue': recent_dialogue,
            'previous_fusion': previous_fusion,
        }
        fused_emotion = fuse_emotions([text_emotion, speech_emotion, face_emotion], temporal_context=temporal_context)
        dialogue = generate_emotional_response(
            recognized_text,
            fused_emotion.get('emotion', '平静'),
            fused_emotion.get('tags', []),
            settings,
            recent_dialogue,
        )

        modalities = {
            'text': text_emotion,
            'speech': speech_emotion,
            'face': face_emotion,
            'fusion': fused_emotion,
        }
        meta = {
            'latency_ms': round((perf_counter() - start_time) * 1000, 1),
            'provider': asr_result.get('provider', 'mock'),
            'audio_format': asr_result.get('format', 'unknown'),
            'pipeline': 'conversation-turn',
        }
        result = speech_result(recognized_text, fused_emotion, modalities=modalities, meta=meta)
        result['dialogue'] = dialogue
        return jsonify(result)
    finally:
        cleanup_audio_path(audio_path)


def parse_recent_dialogue(raw_value: str) -> list[dict]:
    if not raw_value:
        return []
    try:
        import json

        value = json.loads(raw_value)
        return value if isinstance(value, list) else []
    except Exception:
        return []


def parse_previous_fusion(raw_value: str) -> dict:
    if not raw_value:
        return {}
    try:
        import json

        value = json.loads(raw_value)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}
