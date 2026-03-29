def speech_result(text: str, emotion: dict, modalities: dict | None = None, meta: dict | None = None) -> dict:
    result = {
        'text': text,
        'emotion': emotion,
    }

    if modalities is not None:
        result['modalities'] = modalities
    if meta is not None:
        result['meta'] = meta

    return result


def tts_result(audio_url: str, message: str = '', provider: str = 'mock', meta: dict | None = None) -> dict:
    result = {
        'audio_url': audio_url,
        'message': message,
        'provider': provider,
    }

    if meta is not None:
        result['meta'] = meta

    return result
