import json

try:
    import dashscope
    from dashscope import Generation
except ImportError:  # pragma: no cover
    dashscope = None
    Generation = None

from ...schemas.emotion import emotion_result


EMOTION_KEYWORDS = {
    '开心': ['开心', '高兴', '快乐', '兴奋', '满意', '愉快', '欣喜', '好', '棒', '不错'],
    '难过': ['难过', '悲伤', '沮丧', '失望', '痛苦', '伤心', '难受', '委屈'],
    '疲惫': ['累', '疲惫', '疲倦', '困', '疲劳', '乏力', '压力', '辛苦', '焦虑'],
    '感激': ['谢谢', '感谢', '感激', '感恩', '多亏'],
    '平静': ['平静', '正常', '一般', '还行', '可以', '嗯'],
}

TAG_MAP = {
    '开心': ['快乐', '积极', '轻松'],
    '难过': ['悲伤', '需要倾听', '情绪低落'],
    '疲惫': ['压力', '疲惫', '需要安慰'],
    '感激': ['感谢', '温暖', '积极'],
    '平静': ['平静', '中性', '友好'],
}

EMOTIONS = list(EMOTION_KEYWORDS.keys())


def analyze_text_emotion(text: str, settings=None) -> dict:
    if not text:
        distribution = build_default_distribution('平静')
        return emotion_result('平静', 0.5, TAG_MAP['平静'], 'text', distribution=distribution, reliability=0.2, evidence=[])

    provider = getattr(settings, 'text_emotion_provider', 'rules').lower() if settings is not None else 'rules'
    if provider == 'qwen_dashscope':
        result = analyze_text_emotion_with_qwen(text, settings)
        if result is not None:
            return result

    return analyze_text_emotion_with_rules(text)


def analyze_text_emotion_with_rules(text: str) -> dict:
    text_lower = text.lower()
    raw_scores = {}
    evidence = []

    for emotion, keywords in EMOTION_KEYWORDS.items():
        matches = [keyword for keyword in keywords if keyword in text_lower]
        raw_scores[emotion] = len(matches)
        if matches:
            evidence.extend(matches[:2])

    distribution = normalize_scores(raw_scores, fallback='平静')
    best_emotion = max(distribution, key=distribution.get)
    best_score = distribution[best_emotion]
    confidence = 0.45 + best_score * 0.5
    reliability = 0.35 + best_score * 0.45

    if max(raw_scores.values()) == 0:
        confidence = 0.58
        reliability = 0.28

    return emotion_result(
        best_emotion,
        confidence,
        TAG_MAP[best_emotion],
        'text',
        distribution=distribution,
        reliability=reliability,
        evidence=evidence[:3],
    )


def analyze_text_emotion_with_qwen(text: str, settings) -> dict | None:
    if not getattr(settings, 'dashscope_api_key', '') or dashscope is None or Generation is None:
        return None

    dashscope.api_key = settings.dashscope_api_key
    prompt = build_qwen_prompt(text)

    try:
        response = Generation.call(
            model=getattr(settings, 'text_emotion_model', 'qwen-turbo'),
            messages=[
                {'role': 'system', 'content': '你是一个严格输出 JSON 的中文文本情绪识别器。'},
                {'role': 'user', 'content': prompt},
            ],
            result_format='message',
            temperature=0.1,
        )
    except Exception:
        return None

    if getattr(response, 'status_code', 500) != 200:
        return None

    content = extract_generation_content(response)
    payload = parse_json_payload(content)
    if payload is None:
        return None

    emotion = payload.get('emotion', '平静')
    if emotion not in EMOTIONS:
        emotion = '平静'

    confidence = clamp_float(payload.get('confidence', 0.6), 0.0, 1.0)
    evidence = payload.get('evidence', []) if isinstance(payload.get('evidence'), list) else []
    distribution = payload.get('distribution', {}) if isinstance(payload.get('distribution'), dict) else {}
    normalized_distribution = normalize_external_distribution(distribution, emotion)
    reliability = min(0.9, 0.45 + confidence * 0.35)

    return emotion_result(
        emotion,
        confidence,
        TAG_MAP[emotion],
        'text',
        distribution=normalized_distribution,
        reliability=reliability,
        evidence=evidence[:3] or ['qwen-api'],
    )


def build_qwen_prompt(text: str) -> str:
    return (
        '请对下面这段中文文本做情绪识别，只能从以下标签中选择一个作为主情绪：'
        '开心、难过、疲惫、感激、平静。\n'
        '同时给出这 5 类的概率分布，总和必须接近 1。\n'
        '请只返回 JSON，不要输出解释，不要输出 markdown。\n'
        'JSON 格式如下：\n'
        '{"emotion":"平静","confidence":0.78,"distribution":{"开心":0.05,"难过":0.08,"疲惫":0.12,"感激":0.05,"平静":0.70},"evidence":["文本线索1","文本线索2"]}\n'
        f'文本：{text}'
    )


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


def parse_json_payload(content: str) -> dict | None:
    if not content:
        return None

    cleaned = content.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`')
        if cleaned.startswith('json'):
            cleaned = cleaned[4:].strip()

    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None


def normalize_external_distribution(distribution: dict, fallback_emotion: str) -> dict[str, float]:
    normalized = {emotion: clamp_float(distribution.get(emotion, 0.0), 0.0, 1.0) for emotion in EMOTIONS}
    total = sum(normalized.values())
    if total <= 0:
        return build_default_distribution(fallback_emotion)
    return {emotion: normalized[emotion] / total for emotion in EMOTIONS}


def clamp_float(value, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = minimum
    return max(minimum, min(maximum, numeric))


def normalize_scores(raw_scores: dict[str, int], fallback: str) -> dict[str, float]:
    smoothed = {emotion: raw_scores.get(emotion, 0) + 1 for emotion in EMOTIONS}
    total = sum(smoothed.values())
    if total == 0:
        return build_default_distribution(fallback)
    return {emotion: smoothed[emotion] / total for emotion in EMOTIONS}


def build_default_distribution(default_emotion: str) -> dict[str, float]:
    base = {emotion: 0.12 for emotion in EMOTIONS}
    base[default_emotion] = 0.52
    total = sum(base.values())
    return {emotion: score / total for emotion, score in base.items()}
