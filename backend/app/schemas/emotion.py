def emotion_result(
    emotion: str,
    confidence: float,
    tags: list[str],
    source: str,
    distribution: dict | None = None,
    raw_scores: dict | None = None,
    reliability: float | None = None,
    available: bool = True,
    evidence: list[str] | None = None,
) -> dict:
    result = {
        'emotion': emotion,
        'confidence': round(confidence, 2),
        'tags': tags,
        'source': source,
        'available': available,
    }

    if distribution is not None:
        result['distribution'] = {key: round(value, 4) for key, value in distribution.items()}
    if raw_scores is not None:
        result['raw_scores'] = {key: round(value, 4) for key, value in raw_scores.items()}
    if reliability is not None:
        result['reliability'] = round(reliability, 2)
    if evidence is not None:
        result['evidence'] = evidence

    return result


def fused_emotion_result(final_emotion: str, confidence: float, tags: list[str], details: dict) -> dict:
    return {
        'emotion': final_emotion,
        'confidence': round(confidence, 2),
        'tags': tags,
        'details': details,
    }
