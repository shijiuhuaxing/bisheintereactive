from flask import Blueprint, current_app, jsonify, request

from ...schemas.dialogue import dialogue_result
from ...services.llm_service import generate_emotional_response

dialogue_bp = Blueprint('dialogue', __name__)


@dialogue_bp.post('/api/dialogue/respond')
@dialogue_bp.post('/api/generate-response')
def dialogue_response_route():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    emotion = data.get('emotion', '平静')
    context = data.get('context', [])
    recent_dialogue = data.get('recent_dialogue', [])
    settings = current_app.config['SETTINGS']
    response = generate_emotional_response(text, emotion, context, settings, recent_dialogue)
    return jsonify(dialogue_result(
        response=response['response'],
        emotion_style=response['emotion_style'],
        prompt_strategy=response['prompt_strategy'],
        response_emotion_target=response.get('response_emotion_target', ''),
        empathy_strategy=response.get('empathy_strategy', ''),
        tts_emotion=response.get('tts_emotion', emotion),
    ))
