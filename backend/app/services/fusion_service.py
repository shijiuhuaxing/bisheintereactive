from __future__ import annotations

import math
from collections import Counter

from ..schemas.emotion import fused_emotion_result


EMOTIONS = ['开心', '难过', '疲惫', '感激', '平静']

BASE_WEIGHTS = {
    'text': 1.05,
    'speech': 0.9,
    'face': 0.78,
}

MISSING_PENALTY = {
    'text': 1.1,
    'speech': 1.0,
    'face': 1.25,
}


def fuse_emotions(results: list[dict], temporal_context: dict | None = None) -> dict:
    """Fuse modality-level emotion outputs with uncertainty and temporal priors.

    The function keeps the original GitHub API shape but enriches the return value
    with quality, uncertainty, dynamic weights, consistency bonus, conflict penalty,
    temporal prior and final distribution fields used by the frontend debug cards.
    """

    normalized_results = [normalize_modality_result(item) for item in results]
    active_results = [item for item in normalized_results if item['available']]

    if not active_results:
        details = {
            item['source']: build_detail(item, quality=0.0, uncertainty=1.0, weight=0.0)
            for item in normalized_results
        }
        result = fused_emotion_result('平静', 0.5, ['平静', '中性'], details)
        result.update({
            'strategy': 'uncertainty-aware temporal adaptive fusion',
            'distribution': build_peak_distribution('平静', 0.5),
            'top_candidates': [{'emotion': '平静', 'score': 0.5}],
            'agreement_bonus': 0.0,
            'conflict_penalty': 0.0,
            'temporal_prior': build_peak_distribution('平静', 0.45),
        })
        return result

    qualities = {item['source']: estimate_quality(item) for item in normalized_results}
    uncertainties = {item['source']: estimate_uncertainty(item, qualities[item['source']]) for item in normalized_results}
    weights = compute_dynamic_weights(normalized_results, qualities, uncertainties)
    temporal_prior = build_temporal_prior(temporal_context)

    emotion_scores = {emotion: 0.0 for emotion in EMOTIONS}
    for item in normalized_results:
        source = item['source']
        for emotion in EMOTIONS:
            emotion_scores[emotion] += item['distribution'].get(emotion, 0.0) * weights[source]

    agreement_bonus = compute_agreement_bonus(active_results)
    conflict_penalty = compute_conflict_penalty(active_results)

    for emotion in EMOTIONS:
        emotion_scores[emotion] += agreement_bonus.get(emotion, 0.0)
        emotion_scores[emotion] -= conflict_penalty.get(emotion, 0.0)
        emotion_scores[emotion] += temporal_prior.get(emotion, 0.0) * 0.16

    final_distribution = normalize_scores(emotion_scores)
    final_emotion = max(final_distribution, key=final_distribution.get)
    confidence = compute_final_confidence(final_distribution, active_results, weights)
    tags = build_tags(active_results, final_emotion)
    details = {
        item['source']: build_detail(item, qualities[item['source']], uncertainties[item['source']], weights[item['source']])
        for item in normalized_results
    }

    result = fused_emotion_result(final_emotion, confidence, tags, details)
    result.update({
        'strategy': 'uncertainty-aware temporal adaptive fusion',
        'distribution': {emotion: round(score, 4) for emotion, score in final_distribution.items()},
        'top_candidates': [
            {'emotion': emotion, 'score': round(score, 4)}
            for emotion, score in sorted(final_distribution.items(), key=lambda item: item[1], reverse=True)[:3]
        ],
        'agreement_bonus': round(sum(agreement_bonus.values()), 4),
        'conflict_penalty': round(sum(conflict_penalty.values()), 4),
        'temporal_prior': {emotion: round(score, 4) for emotion, score in temporal_prior.items()},
        'modality_weights': {source: round(weight, 4) for source, weight in weights.items()},
    })
    return result


def normalize_modality_result(item: dict) -> dict:
    emotion = normalize_emotion(item.get('emotion', '平静'))
    confidence = clamp(float(item.get('confidence', 0.0)), 0.0, 1.0)
    source = item.get('source', 'unknown')
    available = bool(item.get('available', True))
    distribution = item.get('distribution') or build_peak_distribution(emotion, confidence)
    distribution = normalize_distribution(distribution, emotion)
    reliability = clamp(float(item.get('reliability', confidence if available else 0.0)), 0.0, 1.0)

    return {
        'source': source,
        'emotion': emotion,
        'confidence': confidence,
        'reliability': reliability,
        'available': available,
        'distribution': distribution,
        'tags': item.get('tags', []),
        'evidence': item.get('evidence', []),
        'raw_scores': item.get('raw_scores'),
    }


def normalize_emotion(emotion: str) -> str:
    return emotion if emotion in EMOTIONS else '平静'


def estimate_quality(item: dict) -> float:
    if not item['available']:
        return 0.05

    peak = max(item['distribution'].values())
    entropy = normalized_entropy(item['distribution'])
    evidence_bonus = min(0.12, len(item.get('evidence', [])) * 0.04)
    quality = 0.42 * item['confidence'] + 0.36 * item['reliability'] + 0.22 * peak
    quality = quality * (1 - 0.32 * entropy) + evidence_bonus
    return clamp(quality, 0.04, 0.98)


def estimate_uncertainty(item: dict, quality: float) -> float:
    entropy = normalized_entropy(item['distribution'])
    uncertainty = 0.45 * entropy + 0.35 * (1 - item['confidence']) + 0.2 * (1 - quality)
    if not item['available']:
        uncertainty = max(uncertainty, 0.92)
    return clamp(uncertainty, 0.02, 0.98)


def compute_dynamic_weights(results: list[dict], qualities: dict[str, float], uncertainties: dict[str, float]) -> dict[str, float]:
    logits = {}
    for item in results:
        source = item['source']
        base = BASE_WEIGHTS.get(source, 0.62)
        missing = MISSING_PENALTY.get(source, 1.0) if not item['available'] else 0.0
        logits[source] = base + 1.25 * qualities[source] - 1.1 * uncertainties[source] - missing

    active_sources = [item['source'] for item in results if item['available']]
    if not active_sources:
        return {item['source']: 0.0 for item in results}

    max_logit = max(logits[source] for source in active_sources)
    exp_scores = {
        source: math.exp(logits[source] - max_logit) if source in active_sources else 0.0
        for source in logits
    }
    total = sum(exp_scores.values())
    if total <= 0:
        return {source: (1.0 / len(active_sources) if source in active_sources else 0.0) for source in logits}
    return {source: exp_scores[source] / total for source in logits}


def compute_agreement_bonus(results: list[dict]) -> dict[str, float]:
    bonus = {emotion: 0.0 for emotion in EMOTIONS}
    for index, left in enumerate(results):
        for right in results[index + 1:]:
            if left['emotion'] == right['emotion']:
                strength = min(left['confidence'], right['confidence'], left['reliability'], right['reliability'])
                bonus[left['emotion']] += 0.055 * strength
    return bonus


def compute_conflict_penalty(results: list[dict]) -> dict[str, float]:
    penalty = {emotion: 0.0 for emotion in EMOTIONS}
    for index, left in enumerate(results):
        for right in results[index + 1:]:
            if left['emotion'] == right['emotion']:
                continue
            if left['confidence'] >= 0.62 and right['confidence'] >= 0.62:
                strength = min(left['confidence'], right['confidence']) * 0.035
                penalty[left['emotion']] += strength
                penalty[right['emotion']] += strength
    return penalty


def build_temporal_prior(context: dict | None) -> dict[str, float]:
    if not context:
        return {emotion: 1.0 / len(EMOTIONS) for emotion in EMOTIONS}

    counts = Counter()
    previous = context.get('previous_fusion') or {}
    if previous.get('emotion') in EMOTIONS:
        counts[previous['emotion']] += 2

    for item in context.get('recent_dialogue', [])[-4:]:
        emotion = item.get('emotion')
        if emotion in EMOTIONS:
            counts[emotion] += 1

    if not counts:
        return {emotion: 1.0 / len(EMOTIONS) for emotion in EMOTIONS}

    scores = {emotion: 0.08 for emotion in EMOTIONS}
    for emotion, count in counts.items():
        scores[emotion] += count
    return normalize_scores(scores)


def build_detail(item: dict, quality: float, uncertainty: float, weight: float) -> dict:
    return {
        'emotion': item['emotion'],
        'confidence': round(item['confidence'], 4),
        'reliability': round(item['reliability'], 4),
        'quality': round(quality, 4),
        'uncertainty': round(uncertainty, 4),
        'weight': round(weight, 4),
        'available': item['available'],
        'distribution_peak': round(max(item['distribution'].values()), 4),
        'evidence': item.get('evidence', []),
    }


def compute_final_confidence(distribution: dict[str, float], active_results: list[dict], weights: dict[str, float]) -> float:
    ordered = sorted(distribution.values(), reverse=True)
    peak = ordered[0]
    margin = peak - ordered[1] if len(ordered) > 1 else peak
    active_weight = sum(weights.get(item['source'], 0.0) for item in active_results)
    confidence = 0.36 + peak * 0.42 + margin * 0.18 + min(0.04, active_weight * 0.04)
    return clamp(confidence, 0.35, 0.96)


def build_peak_distribution(emotion: str, confidence: float) -> dict[str, float]:
    emotion = normalize_emotion(emotion)
    confidence = clamp(confidence, 0.0, 1.0)
    remainder = max(0.0, 1.0 - confidence)
    others = [item for item in EMOTIONS if item != emotion]
    distribution = {item: remainder / len(others) for item in others}
    distribution[emotion] = max(confidence, 0.36)
    return normalize_scores(distribution)


def normalize_distribution(distribution: dict, fallback_emotion: str) -> dict[str, float]:
    normalized = {emotion: max(0.0, float(distribution.get(emotion, 0.0))) for emotion in EMOTIONS}
    if sum(normalized.values()) <= 0:
        return build_peak_distribution(fallback_emotion, 0.5)
    return normalize_scores(normalized)


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in scores.values())
    if total <= 0:
        return {emotion: 1.0 / len(EMOTIONS) for emotion in EMOTIONS}
    return {emotion: max(scores.get(emotion, 0.0), 0.0) / total for emotion in EMOTIONS}


def normalized_entropy(distribution: dict[str, float]) -> float:
    probs = [max(0.0, float(distribution.get(emotion, 0.0))) for emotion in EMOTIONS]
    total = sum(probs)
    if total <= 0:
        return 1.0
    entropy = 0.0
    for prob in probs:
        if prob > 0:
            p = prob / total
            entropy -= p * math.log(p)
    return clamp(entropy / math.log(len(EMOTIONS)), 0.0, 1.0)


def build_tags(results: list[dict], final_emotion: str) -> list[str]:
    merged = []
    for item in results:
        for tag in item.get('tags', []):
            if tag not in merged:
                merged.append(tag)
    if final_emotion not in merged:
        merged.insert(0, final_emotion)
    return merged[:4]


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
