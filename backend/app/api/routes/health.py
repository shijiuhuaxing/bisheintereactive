from flask import Blueprint, current_app, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.get('/api/health')
def health_check():
    settings = current_app.config['SETTINGS']
    return jsonify({
        'status': 'ok',
        'use_mock_services': settings.use_mock_services,
        'dashscope_configured': bool(settings.dashscope_api_key),
    })
