from pathlib import Path
import random

try:
    import dashscope
    from dashscope import Generation
except ImportError:  # pragma: no cover
    dashscope = None
    Generation = None


PROMPT_PATH = Path(__file__).resolve().parents[1] / 'prompts' / 'companion_prompt.txt'

MOCK_RESPONSES = {
    '开心': [
        '太好了，听到你状态不错，我也很开心。',
        '你的好心情很有感染力，我们继续聊聊吧。',
    ],
    '难过': [
        '我感受到你有些难过，我先陪着你。',
        '别着急，你可以慢慢说，我会认真听。',
    ],
    '疲惫': [
        '听起来你有点累了，先缓一缓也没关系。',
        '辛苦了，我们先把最烦的一件事慢慢理顺。',
    ],
    '感激': [
        '谢谢你的表达，这让我觉得很温暖。',
        '收到你的感谢了，我会继续认真陪着你。',
    ],
    '平静': [
        '我在这里，想聊什么都可以。',
        '好的，我会认真听你说。',
    ],
}


def generate_emotional_response(
    text: str,
    emotion: str,
    context: list[str] | None = None,
    settings=None,
    recent_dialogue: list[dict] | None = None,
) -> dict:
    provider = getattr(settings, 'llm_provider', 'mock').lower() if settings is not None else 'mock'
    if provider == 'qwen_dashscope':
        result = generate_with_qwen(text, emotion, context or [], settings, recent_dialogue or [])
        if result is not None:
            return result

    responses = MOCK_RESPONSES.get(emotion, MOCK_RESPONSES['平静'])
    response_text = random.choice(responses)
    return {
        'response': normalize_response_length(response_text),
        'emotion_style': emotion,
        'prompt_strategy': 'emotion-guided-mock',
        'response_emotion_target': infer_response_emotion_target(emotion),
        'empathy_strategy': infer_empathy_strategy(emotion),
        'tts_emotion': infer_tts_emotion(emotion),
    }


def generate_with_qwen(text: str, emotion: str, context: list[str], settings, recent_dialogue: list[dict]) -> dict | None:
    if settings is None or not getattr(settings, 'dashscope_api_key', '') or dashscope is None or Generation is None:
        return None

    dashscope.api_key = settings.dashscope_api_key
    system_prompt = load_prompt_template()
    user_prompt = build_structured_user_prompt(text, emotion, context, recent_dialogue)

    try:
        response = Generation.call(
            model=getattr(settings, 'llm_model', 'qwen-turbo'),
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            result_format='message',
            temperature=0.6,
            top_p=0.85,
        )
    except Exception:
        return None

    if getattr(response, 'status_code', 500) != 200:
        return None

    content = extract_generation_content(response)
    if not content:
        return None

    return {
        'response': normalize_response_length(clean_response_text(content), text, emotion),
        'emotion_style': emotion,
        'prompt_strategy': 'emotion-guided-qwen-structured',
        'response_emotion_target': infer_response_emotion_target(emotion),
        'empathy_strategy': infer_empathy_strategy(emotion),
        'tts_emotion': infer_tts_emotion(emotion),
    }


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding='utf-8').strip()


def build_structured_user_prompt(text: str, emotion: str, context: list[str], recent_dialogue: list[dict]) -> str:
    confidence_hint = infer_confidence_hint(context)
    context_text = '、'.join(context[:4]) if context else '无'
    dialogue_text = format_recent_dialogue(recent_dialogue)
    response_emotion_target = infer_response_emotion_target(emotion)
    empathy_strategy = infer_empathy_strategy(emotion)
    return (
        '请根据以下结构化输入生成适合直接朗读、也适合继续对话的中文陪伴回复。\n\n'
        f'user_text: {text}\n'
        f'detected_emotion: {emotion}\n'
        f'emotion_confidence: {confidence_hint}\n'
        f'emotion_tags: {context_text}\n'
        f'recent_context: {context_text}\n'
        f'recent_dialogue: {dialogue_text}\n'
        f'response_emotion_target: {response_emotion_target}\n'
        f'empathy_strategy: {empathy_strategy}\n\n'
        '请注意：回复要自然、共情、适合 TTS 朗读，并体现陪伴者自身情绪；是否简短由语境决定。'
    )


def infer_confidence_hint(context: list[str]) -> str:
    if not context:
        return '0.60'
    if len(context) >= 3:
        return '0.82'
    return '0.72'


def infer_response_emotion_target(emotion: str) -> str:
    mapping = {
        '开心': '被感染的开心与轻松',
        '难过': '温柔的心疼与陪伴式难过',
        '疲惫': '安稳、轻柔、托住对方的平缓情绪',
        '感激': '温暖、真诚、被触动的回应情绪',
        '平静': '自然、稳定、开放的陪伴状态',
    }
    return mapping.get(emotion, mapping['平静'])


def infer_empathy_strategy(emotion: str) -> str:
    mapping = {
        '开心': '先接住用户的好心情，再用轻快语气顺势延展话题。',
        '难过': '先表达陪伴和心疼，再用低缓语气安抚，不要急着给建议。',
        '疲惫': '先减压和安抚，再用稳定柔和的句子让对方放松。',
        '感激': '先温暖回应，再表达珍惜和继续陪伴。',
        '平静': '先自然回应，再轻柔地引导继续交流。',
    }
    return mapping.get(emotion, mapping['平静'])


def infer_tts_emotion(emotion: str) -> str:
    mapping = {
        '开心': '开心',
        '难过': '难过',
        '疲惫': '疲惫',
        '感激': '感激',
        '平静': '平静',
    }
    return mapping.get(emotion, '平静')


def format_recent_dialogue(recent_dialogue: list[dict]) -> str:
    if not recent_dialogue:
        return '无'

    lines = []
    for turn in recent_dialogue[-4:]:
        user_text = (turn.get('user') or '').strip()
        assistant_text = (turn.get('assistant') or '').strip()
        emotion = (turn.get('emotion') or '').strip()
        if user_text:
            lines.append(f'用户({emotion or "未知"}): {user_text}')
        if assistant_text:
            lines.append(f'助手: {assistant_text}')
    return ' | '.join(lines) if lines else '无'


def extract_generation_content(response) -> str:
    output = getattr(response, 'output', None)
    if output is None:
        return ''

    choices = None
    if isinstance(output, dict):
        choices = output.get('choices', [])
    elif hasattr(output, 'choices'):
        choices = output.choices

    if not choices:
        return ''

    first_choice = choices[0]
    message = first_choice.get('message') if isinstance(first_choice, dict) else getattr(first_choice, 'message', None)
    if isinstance(message, dict):
        return message.get('content', '')
    return getattr(message, 'content', '') if message is not None else ''


def clean_response_text(text: str) -> str:
    return text.strip().replace('\n', '').replace('\r', '')


def normalize_response_length(text: str, user_text: str = '', emotion: str = '平静') -> str:
    max_length = choose_response_limit(user_text, emotion)
    if len(text) <= max_length:
        return text
    trimmed = text[:max_length].rstrip('，。！？,.!?')
    return f'{trimmed}。'


def choose_response_limit(user_text: str, emotion: str) -> int:
    deep_cues = ['为什么', '怎么办', '好累', '撑不住', '难过', '委屈', '焦虑', '痛苦', '崩溃', '孤独']
    if emotion in ('难过', '疲惫') or any(cue in user_text for cue in deep_cues) or len(user_text) >= 18:
        return 72
    return 44
