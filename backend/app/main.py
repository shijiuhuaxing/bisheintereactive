from flask import Flask
from flask_cors import CORS

from .api.routes.dialogue import dialogue_bp
from .api.routes.emotion import emotion_bp
from .api.routes.health import health_bp
from .api.routes.speech import speech_bp
from .api.routes.tts import tts_bp
from .config import get_settings
from .utils.logger import configure_logging


def create_app() -> Flask:
    configure_logging()
    settings = get_settings()

    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    app.config['SETTINGS'] = settings

    cors_origin_list = [origin.strip() for origin in settings.cors_origins.split(',') if origin.strip()]
    CORS(app, resources={r'/api/*': {'origins': cors_origin_list or ['*']}})

    app.register_blueprint(health_bp)
    app.register_blueprint(speech_bp)
    app.register_blueprint(emotion_bp)
    app.register_blueprint(dialogue_bp)
    app.register_blueprint(tts_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    settings = app.config['SETTINGS']
    app.run(host=settings.app_host, port=settings.app_port, debug=settings.app_debug)
