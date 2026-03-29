from ..schemas.emotion import fused_emotion_result


BASE_WEIGHTS = {
    'text': 1.0,
    'speech': 0.9,
    'face': 0.7,
}

EMOTIONS = ['开心', '难过', '疲惫', '感激', '平静']


def fuse_emotions(results: list[dict]) -> dict:
    active_results = [item for item in results if item.get('available', True)]
    details = {}
    aggregated = {emotion: 0.0 for emotion in EMOTIONS}
    agreement_pairs = []

    for item in results:
        source = item.get('source', 'unknown')
        confidence = float(item.get('confidence', 0.0))
        reliability = float(item.get('reliability', confidence))
        distribution = item.get('distribution') or build_peak_distribution(item.get('emotion', '平静'), confidence)
        base_weight = BASE_WEIGHTS.get(source, 0.6)
        available = item.get('available', True)

        source_weight = base_weight * reliability if available else 0.0

        for emotion in EMOTIONS:
            aggregated[emotion] += distribution.get(emotion, 0.0) * source_weight

        details[source] = {
            'emotion': item.get('emotion', '平静'),
            'confidence': round(confidence, 2),
            'reliability': round(reliability, 2),
            'weight': round(source_weight, 2),
            'available': available,
            'distribution_peak': round(max(distribution.values()), 2),
            'evidence': item.get('evidence', []),
        }

    if not active_results:
        result = fused_emotion_result('平静', 0.5, ['平静', '中性'], details)
        result['top_candidates'] = [{'emotion': '平静', 'score': 0.5}]
        result['strategy'] = 'reliability-aware late fusion'
        result['agreement_bonus'] = 0.0
        return result

    agreement_bonus = compute_agreement_bonus(active_results, agreement_pairs)
    for emotion, bonus in agreement_bonus.items():
        aggregated[emotion] += bonus

    final_emotion = max(aggregated, key=aggregated.get)
    normalized = normalize_scores(aggregated)
    final_confidence = min(0.96, 0.45 + normalized[final_emotion] * 0.55)
    tags = build_tags(active_results, final_emotion)

    result = fused_emotion_result(final_emotion, final_confidence, tags, details)
    result['top_candidates'] = [
        {'emotion': emotion, 'score': round(score, 3)}
        for emotion, score in sorted(normalized.items(), key=lambda item: item[1], reverse=True)[:3]
    ]
    result['strategy'] = 'reliability-aware late fusion'
    result['agreement_bonus'] = round(sum(agreement_bonus.values()), 3)
    result['agreement_pairs'] = agreement_pairs
    return result


def compute_agreement_bonus(results: list[dict], agreement_pairs: list[list[str]]) -> dict[str, float]:
    bonus = {emotion: 0.0 for emotion in EMOTIONS}
    for index, left in enumerate(results):
        for right in results[index + 1:]:
            if left.get('emotion') == right.get('emotion'):
                agreed_emotion = left['emotion']
                pair_bonus = 0.05 * min(float(left.get('confidence', 0.0)), float(right.get('confidence', 0.0)))
                bonus[agreed_emotion] += pair_bonus
                agreement_pairs.append([left.get('source', 'unknown'), right.get('source', 'unknown'), agreed_emotion])
    return bonus


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in scores.values())
    if total <= 0:
        return {emotion: 0.0 for emotion in EMOTIONS}
    return {emotion: max(scores[emotion], 0.0) / total for emotion in EMOTIONS}


def build_peak_distribution(emotion: str, confidence: float) -> dict[str, float]:
    base = {item: 0.08 for item in EMOTIONS}
    base[emotion] = max(0.4, confidence)
    total = sum(base.values())
    return {item: score / total for item, score in base.items()}


def build_tags(results: list[dict], final_emotion: str) -> list[str]:
    merged = []
    for item in results:
        for tag in item.get('tags', []):
            if tag not in merged:
                merged.append(tag)

    if not merged:
        merged = [final_emotion]
    return merged[:4]
