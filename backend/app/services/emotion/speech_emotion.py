import librosa
import torch
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

from ...schemas.emotion import emotion_result


EMOTION_CUES = {
    '开心': ['哈哈', '开心', '高兴', '真好', '太好了', '快乐'],
    '难过': ['难过', '伤心', '委屈', '不开心', '糟糕', '烦'],
    '疲惫': ['累', '压力', '辛苦', '疲惫', '好困', '撑不住', '焦虑'],
    '感激': ['谢谢', '感谢', '麻烦你了', '感激'],
    '平静': ['可以', '还好', '一般', '嗯', '好的'],
}

TAG_MAP = {
    '开心': ['快乐', '积极', '轻松'],
    '难过': ['悲伤', '需要倾听', '情绪低落'],
    '疲惫': ['压力', '疲惫', '需要安慰'],
    '感激': ['感谢', '温暖', '积极'],
    '平静': ['平静', '中性'],
}

EMOTIONS = list(EMOTION_CUES.keys())
_SPEECH_MODEL = None
_SPEECH_EXTRACTOR = None


def analyze_speech_emotion(text: str = '', audio_path: str | None = None, settings=None) -> dict:
    provider = getattr(settings, 'speech_emotion_provider', 'rules').lower() if settings is not None else 'rules'

    if audio_path and provider == 'wav2vec2_superb':
        result = analyze_speech_emotion_with_model(audio_path, text, settings)
        if result is not None:
            return result

    return analyze_speech_emotion_with_rules(text)


def analyze_speech_emotion_with_model(audio_path: str, text: str, settings) -> dict | None:
    try:
        feature_extractor, model = get_speech_model(settings)
        waveform, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
        inputs = feature_extractor(waveform, sampling_rate=16000, return_tensors='pt', padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits[0]
        probs = torch.softmax(logits, dim=-1).cpu().tolist()
    except Exception:
        return None

    id2label = model.config.id2label
    raw_scores = {str(id2label[index]): float(score) for index, score in enumerate(probs)}
    distribution = map_superb_distribution(raw_scores, text)
    emotion = max(distribution, key=distribution.get)
    confidence = 0.42 + distribution[emotion] * 0.5
    top_label = max(raw_scores, key=raw_scores.get)
    reliability = min(0.88, 0.42 + raw_scores[top_label] * 0.42)
    evidence = [f'speech-top={top_label}:{raw_scores[top_label]:.2f}']

    if text:
        evidence.extend(extract_text_cues(text))

    return emotion_result(
        emotion,
        confidence,
        TAG_MAP[emotion],
        'speech',
        distribution=distribution,
        raw_scores=raw_scores,
        reliability=reliability,
        evidence=evidence[:3],
    )


def get_speech_model(settings):
    global _SPEECH_EXTRACTOR, _SPEECH_MODEL
    if _SPEECH_EXTRACTOR is None or _SPEECH_MODEL is None:
        model_name = getattr(settings, 'speech_emotion_model', 'superb/wav2vec2-base-superb-er')
        _SPEECH_EXTRACTOR = AutoFeatureExtractor.from_pretrained(model_name)
        _SPEECH_MODEL = AutoModelForAudioClassification.from_pretrained(model_name)
        _SPEECH_MODEL.eval()
    return _SPEECH_EXTRACTOR, _SPEECH_MODEL


def map_superb_distribution(raw_scores: dict[str, float], text: str) -> dict[str, float]:
    neu = raw_scores.get('neu', 0.0)
    hap = raw_scores.get('hap', 0.0)
    ang = raw_scores.get('ang', 0.0)
    sad = raw_scores.get('sad', 0.0)

    text_bias = extract_text_bias(text)
    distribution = {
        '开心': hap * 1.05 + text_bias['开心'] * 0.18,
        '难过': sad * 0.82 + ang * 0.72 + text_bias['难过'] * 0.18,
        '疲惫': sad * 0.28 + neu * 0.26 + text_bias['疲惫'] * 0.22,
        '感激': hap * 0.24 + text_bias['感激'] * 0.3,
        '平静': neu * 0.82 + text_bias['平静'] * 0.12,
    }

    total = sum(distribution.values())
    if total <= 0:
        return build_default_distribution('平静')
    return {emotion: score / total for emotion, score in distribution.items()}


def analyze_speech_emotion_with_rules(text: str = '') -> dict:
    if not text:
        distribution = build_default_distribution('平静')
        return emotion_result('平静', 0.52, TAG_MAP['平静'], 'speech', distribution=distribution, reliability=0.2, evidence=[])

    text_lower = text.lower()
    weighted_scores = {emotion: 1.0 for emotion in EMOTIONS}
    evidence = []

    for emotion, cues in EMOTION_CUES.items():
        hits = [cue for cue in cues if cue in text_lower]
        weighted_scores[emotion] += len(hits) * cue_weight(emotion)
        if hits:
            evidence.extend(hits[:2])

    if '...' in text or '……' in text:
        weighted_scores['疲惫'] += 0.8
        weighted_scores['难过'] += 0.4
    if '！' in text or '!' in text:
        weighted_scores['开心'] += 0.5
    if len(text) <= 6:
        weighted_scores['平静'] += 0.4

    total = sum(weighted_scores.values())
    distribution = {emotion: weighted_scores[emotion] / total for emotion in EMOTIONS}
    best_emotion = max(distribution, key=distribution.get)
    best_score = distribution[best_emotion]

    confidence = 0.42 + best_score * 0.48
    reliability = 0.3 + best_score * 0.4

    return emotion_result(
        best_emotion,
        confidence,
        TAG_MAP[best_emotion],
        'speech',
        distribution=distribution,
        reliability=reliability,
        evidence=evidence[:3],
    )


def extract_text_bias(text: str) -> dict[str, float]:
    bias = {emotion: 0.0 for emotion in EMOTIONS}
    text_lower = (text or '').lower()
    for emotion, cues in EMOTION_CUES.items():
        bias[emotion] = float(sum(1 for cue in cues if cue in text_lower))
    return bias


def extract_text_cues(text: str) -> list[str]:
    text_lower = (text or '').lower()
    evidence = []
    for cues in EMOTION_CUES.values():
        for cue in cues:
            if cue in text_lower and cue not in evidence:
                evidence.append(cue)
    return evidence[:2]


def cue_weight(emotion: str) -> float:
    return {
        '疲惫': 1.2,
        '难过': 1.15,
        '开心': 1.1,
        '感激': 1.05,
        '平静': 0.8,
    }.get(emotion, 1.0)


def build_default_distribution(default_emotion: str) -> dict[str, float]:
    base = {emotion: 0.13 for emotion in EMOTIONS}
    base[default_emotion] = 0.48
    total = sum(base.values())
    return {emotion: score / total for emotion, score in base.items()}
