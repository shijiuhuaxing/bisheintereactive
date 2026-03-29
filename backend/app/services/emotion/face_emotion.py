from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

from ...schemas.emotion import emotion_result

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover
    ort = None


_FACE_CASCADE = None
_EMOTION_SESSION = None
EMOTION_MODEL_PATH = Path(__file__).resolve().parents[4] / 'models' / 'checkpoints' / 'emotion-ferplus-8.onnx'
FERPLUS_LABELS = ['neutral', 'happiness', 'surprise', 'sadness', 'anger', 'disgust', 'fear', 'contempt']


def analyze_face_emotion(image_file=None, frame_hint: str | None = None) -> dict:
    if image_file is None:
        return unavailable_result('未检测到视频帧')

    image_bytes = image_file.read()
    image_file.stream.seek(0)
    if not image_bytes:
        return unavailable_result('视频帧为空')

    image = decode_image(image_bytes)
    if image is None:
        return unavailable_result('无法解码上传图像')

    session = get_emotion_session()
    cascade = get_face_cascade()
    if session is None:
        return unavailable_result('ONNX 表情模型未就绪')
    if cascade is None:
        return unavailable_result('人脸检测器未就绪')

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return unavailable_result('未检测到人脸')

    x, y, w, h = max(faces, key=lambda item: item[2] * item[3])
    face_roi = gray[y:y + h, x:x + w]
    input_tensor = preprocess_face(face_roi)

    try:
        input_name = session.get_inputs()[0].name
        output_scores = session.run(None, {input_name: input_tensor})[0][0]
    except Exception as exc:  # pragma: no cover
        return unavailable_result(f'ONNX 推理失败: {exc}')

    fer_distribution = softmax(output_scores)
    raw_emotions = {label: float(score) for label, score in zip(FERPLUS_LABELS, fer_distribution)}
    distribution = convert_ferplus_distribution(raw_emotions)
    final_emotion = max(distribution, key=distribution.get)

    top_two = sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:2]
    confidence = 0.42 + top_two[0][1] * 0.5
    margin = top_two[0][1] - (top_two[1][1] if len(top_two) > 1 else 0.0)
    reliability = min(0.94, 0.48 + margin * 0.9)
    fer_top = max(raw_emotions, key=raw_emotions.get)

    tags = {
        '开心': ['模型检测正向表情', '高兴或惊喜'],
        '难过': ['模型检测负向表情', '悲伤或愤怒'],
        '疲惫': ['模型检测低活跃状态', '中性偏低落'],
        '感激': ['模型检测柔和积极表情', '温和正向'],
        '平静': ['模型检测中性表情', '状态稳定'],
    }[final_emotion]

    evidence = [
        f'box={w}x{h}',
        f'ferplus-top={fer_top}:{raw_emotions[fer_top]:.2f}',
        f'margin={margin:.2f}',
    ]

    return emotion_result(
        final_emotion,
        confidence,
        tags,
        'face',
        distribution=distribution,
        raw_scores=raw_emotions,
        reliability=reliability,
        available=True,
        evidence=evidence,
    )


def get_emotion_session():
    global _EMOTION_SESSION
    if ort is None:
        return None
    if _EMOTION_SESSION is None:
        model_path = ensure_ascii_model_file()
        _EMOTION_SESSION = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
    return _EMOTION_SESSION


def get_face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        cascade_path = ensure_ascii_cascade_file()
        cascade = cv2.CascadeClassifier(str(cascade_path))
        if cascade.empty():
            return None
        _FACE_CASCADE = cascade
    return _FACE_CASCADE


def ensure_ascii_asset_dir() -> Path:
    asset_dir = Path(tempfile.gettempdir()) / 'virtual_companion_assets'
    asset_dir.mkdir(parents=True, exist_ok=True)
    return asset_dir


def ensure_ascii_cascade_file() -> Path:
    asset_dir = ensure_ascii_asset_dir()
    source = Path(cv2.data.haarcascades) / 'haarcascade_frontalface_default.xml'
    target = asset_dir / 'haarcascade_frontalface_default.xml'
    if not target.exists():
        shutil.copyfile(source, target)
    return target


def ensure_ascii_model_file() -> Path:
    if not EMOTION_MODEL_PATH.exists():
        raise FileNotFoundError(f'缺少 ONNX 模型文件: {EMOTION_MODEL_PATH}')
    asset_dir = ensure_ascii_asset_dir()
    target = asset_dir / EMOTION_MODEL_PATH.name
    if not target.exists() or target.stat().st_size != EMOTION_MODEL_PATH.stat().st_size:
        shutil.copyfile(EMOTION_MODEL_PATH, target)
    return target


def decode_image(image_bytes: bytes):
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    if array.size == 0:
        return None
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def preprocess_face(face_roi: np.ndarray) -> np.ndarray:
    resized = cv2.resize(face_roi, (64, 64), interpolation=cv2.INTER_AREA)
    resized = resized.astype(np.float32)
    return resized[np.newaxis, np.newaxis, :, :]


def softmax(scores: np.ndarray) -> np.ndarray:
    scores = scores - np.max(scores)
    exp = np.exp(scores)
    return exp / np.sum(exp)


def convert_ferplus_distribution(raw_emotions: dict[str, float]) -> dict[str, float]:
    happiness = raw_emotions.get('happiness', 0.0)
    surprise = raw_emotions.get('surprise', 0.0)
    neutral = raw_emotions.get('neutral', 0.0)
    sadness = raw_emotions.get('sadness', 0.0)
    anger = raw_emotions.get('anger', 0.0)
    fear = raw_emotions.get('fear', 0.0)
    disgust = raw_emotions.get('disgust', 0.0)
    contempt = raw_emotions.get('contempt', 0.0)

    smile_bonus = 0.18 if happiness >= 0.45 else 0.0
    neutral_penalty = 0.12 if happiness >= 0.35 else 0.0

    distribution = {
        '开心': happiness * 1.3 + surprise * 0.42 + smile_bonus,
        '难过': sadness * 1.0 + anger * 0.72 + fear * 0.5 + disgust * 0.42,
        '疲惫': neutral * 0.18 + sadness * 0.16 + contempt * 0.18 + fear * 0.08,
        '感激': happiness * 0.52 + neutral * 0.18 + surprise * 0.12,
        '平静': max(0.0, neutral * 1.05 - neutral_penalty) + contempt * 0.06,
    }

    total = sum(distribution.values())
    if total <= 0:
        return {'开心': 0.12, '难过': 0.12, '疲惫': 0.12, '感激': 0.1, '平静': 0.54}
    return {emotion: score / total for emotion, score in distribution.items()}


def unavailable_result(reason: str) -> dict:
    distribution = {
        '开心': 0.12,
        '难过': 0.12,
        '疲惫': 0.12,
        '感激': 0.1,
        '平静': 0.54,
    }
    return emotion_result(
        '平静',
        0.2,
        ['表情通道未触发'],
        'face',
        distribution=distribution,
        reliability=0.0,
        available=False,
        evidence=[reason],
    )
