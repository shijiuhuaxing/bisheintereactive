from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from ...services.tts_service import synthesize_speech

tts_bp = Blueprint('tts', __name__)
OUTPUT_DIR = Path(__file__).resolve().parents[4] / 'outputs' / 'audios'


@tts_bp.post('/api/tts/synthesize')
@tts_bp.post('/api/text-to-speech')
def tts_route():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    emotion = data.get('emotion', '平静')
    settings = current_app.config['SETTINGS']
    base_url = request.host_url.rstrip('/')
    return jsonify(synthesize_speech(text, emotion, settings, base_url))


@tts_bp.get('/api/tts/files/<path:filename>')
def serve_tts_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=False)
