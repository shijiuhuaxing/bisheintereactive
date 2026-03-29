def dialogue_result(
    response: str,
    emotion_style: str,
    prompt_strategy: str = 'emotion-guided',
    response_emotion_target: str = '',
    empathy_strategy: str = '',
    tts_emotion: str = '',
) -> dict:
    return {
        'response': response,
        'emotion_style': emotion_style,
        'prompt_strategy': prompt_strategy,
        'response_emotion_target': response_emotion_target,
        'empathy_strategy': empathy_strategy,
        'tts_emotion': tts_emotion or emotion_style,
    }
