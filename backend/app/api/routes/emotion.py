from flask import Blueprint, current_app, jsonify, request

from ...services.emotion.face_emotion import analyze_face_emotion
from ...services.emotion.speech_emotion import analyze_speech_emotion
from ...services.emotion.text_emotion import analyze_text_emotion
from ...services.fusion_service import fuse_emotions

emotion_bp = Blueprint('emotion', __name__)


@emotion_bp.post('/api/emotion/text')
def text_emotion_route():
    data = request.get_json(silent=True) or {}
    settings = current_app.config['SETTINGS']
    return jsonify(analyze_text_emotion(data.get('text', ''), settings))


@emotion_bp.post('/api/emotion/speech')
def speech_emotion_route():
    data = request.get_json(silent=True) or {}
    settings = current_app.config['SETTINGS']
    return jsonify(analyze_speech_emotion(data.get('text', ''), settings=settings))


@emotion_bp.post('/api/emotion/face')
def face_emotion_route():
    frame_file = request.files.get('frame') if request.files else None
    if frame_file is not None:
        return jsonify(analyze_face_emotion(frame_file))

    data = request.get_json(silent=True) or {}
    return jsonify(analyze_face_emotion(data.get('frame_hint')))


@emotion_bp.post('/api/emotion/fuse')
def fuse_emotion_route():
    data = request.get_json(silent=True) or {}
    return jsonify(fuse_emotions(data.get('results', [])))
