from __future__ import annotations

import asyncio
import base64
import os
import uuid
from io import BytesIO
from time import perf_counter

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.services.asr_service import cleanup_audio_path, recognize_audio
from backend.app.services.emotion.face_emotion import analyze_face_emotion
from backend.app.services.emotion.speech_emotion import analyze_speech_emotion
from backend.app.services.emotion.text_emotion import analyze_text_emotion
from backend.app.services.fusion_service import fuse_emotions
from backend.app.services.llm_service import generate_emotional_response
from backend.app.services.tts_service import synthesize_speech
from backend.realtime.schemas import error_payload, event_payload
from backend.realtime.session_manager import session_manager


class MemoryUpload:
    def __init__(self, content: bytes, filename: str, mimetype: str) -> None:
        self._content = content
        self.filename = filename
        self.mimetype = mimetype
        self.stream = BytesIO(content)

    def read(self, *args, **kwargs) -> bytes:
        return self.stream.read(*args, **kwargs)

    def save(self, target: str) -> None:
        with open(target, 'wb') as file:
            file.write(self._content)


settings = get_settings()
app = FastAPI(title='Virtual Companion Realtime Service')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
async def health() -> dict:
    return {'status': 'ok', 'service': 'realtime'}


@app.websocket('/ws/realtime')
async def realtime_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = str(uuid.uuid4())
    state = session_manager.get(session_id)
    await websocket.send_json(event_payload('session.ready', session_id=session_id))

    try:
        while True:
            message = await websocket.receive_json()
            event_type = message.get('type', '')
            turn_id = message.get('turn_id') or str(uuid.uuid4())

            if event_type == 'ping':
                await websocket.send_json(event_payload('pong', turn_id, session_id=session_id))
            elif event_type == 'face.snapshot':
                await handle_face_snapshot(websocket, state, message, turn_id)
            elif event_type == 'audio.final':
                await handle_audio_turn(websocket, state, message, turn_id)
            elif event_type == 'interrupt':
                await websocket.send_json(event_payload('turn.interrupted', turn_id))
            else:
                await websocket.send_json(error_payload(f'未知实时事件类型: {event_type}', turn_id))
    except WebSocketDisconnect:
        session_manager.remove(session_id)


async def handle_face_snapshot(websocket: WebSocket, state, message: dict, turn_id: str) -> None:
    try:
        frame = decode_data_url(message.get('image_base64', ''))
        frame_file = MemoryUpload(frame, 'frame.jpg', 'image/jpeg') if frame else None
        face_emotion = await asyncio.to_thread(analyze_face_emotion, frame_file)
        state.latest_face = face_emotion
        await websocket.send_json(event_payload('face.update', turn_id, face=face_emotion))
    except Exception as exc:
        await websocket.send_json(error_payload(f'表情实时识别失败: {exc}', turn_id))


async def handle_audio_turn(websocket: WebSocket, state, message: dict, turn_id: str) -> None:
    start = perf_counter()
    audio_path = None
    try:
        await websocket.send_json(event_payload('turn.started', turn_id))
        audio_bytes = decode_data_url(message.get('audio_base64', ''))
        if not audio_bytes:
            await websocket.send_json(error_payload('未收到有效音频数据', turn_id))
            return

        audio_format = message.get('audio_format', 'wav')
        audio_file = MemoryUpload(audio_bytes, f'recording.{audio_format}', f'audio/{audio_format}')
        asr_result = await asyncio.to_thread(recognize_audio, audio_file, settings)
        recognized_text = asr_result.get('text', '')
        audio_path = asr_result.get('audio_path')
        await websocket.send_json(event_payload('asr.final', turn_id, text=recognized_text, meta={
            'provider': asr_result.get('provider', 'unknown'),
            'audio_format': asr_result.get('format', audio_format),
        }))

        frame_file = None
        if message.get('image_base64'):
            frame_bytes = decode_data_url(message.get('image_base64', ''))
            frame_file = MemoryUpload(frame_bytes, 'frame.jpg', 'image/jpeg') if frame_bytes else None

        text_task = asyncio.create_task(asyncio.to_thread(analyze_text_emotion, recognized_text, settings))
        face_task = asyncio.create_task(
            asyncio.to_thread(analyze_face_emotion, frame_file)
            if frame_file else asyncio.to_thread(lambda: state.latest_face or analyze_face_emotion(None))
        )
        speech_task = asyncio.create_task(asyncio.to_thread(analyze_speech_emotion, recognized_text, audio_path, settings))

        text_emotion, face_emotion = await asyncio.gather(text_task, face_task)
        speech_placeholder = build_pending_speech_emotion()
        fused_emotion = await asyncio.to_thread(
            fuse_emotions,
            [text_emotion, speech_placeholder, face_emotion],
            {
                'recent_dialogue': state.recent_dialogue,
                'previous_fusion': state.previous_fusion or {},
            },
        )
        state.previous_fusion = fused_emotion
        modalities = {
            'text': text_emotion,
            'speech': speech_placeholder,
            'face': face_emotion,
            'fusion': fused_emotion,
        }
        meta = {
            'latency_ms': round((perf_counter() - start) * 1000, 1),
            'provider': asr_result.get('provider', 'unknown'),
            'audio_format': asr_result.get('format', audio_format),
            'transport': 'websocket',
            'stage': 'fast-preview',
        }
        await websocket.send_json(event_payload('emotion.update', turn_id, emotion=fused_emotion, modalities=modalities, meta=meta))

        dialogue = await asyncio.to_thread(
            generate_emotional_response,
            recognized_text,
            fused_emotion.get('emotion', '平静'),
            fused_emotion.get('tags', []),
            settings,
            state.recent_dialogue,
        )
        await websocket.send_json(event_payload('response.text', turn_id, dialogue=dialogue, text=dialogue.get('response', '')))
        state.append_dialogue(recognized_text, dialogue.get('response', ''), fused_emotion.get('emotion', '平静'))
        await websocket.send_json(event_payload('turn.done', turn_id, meta={**meta, 'response_ms': round((perf_counter() - start) * 1000, 1)}))

        try:
            speech_emotion = await asyncio.wait_for(speech_task, timeout=6.0)
            final_fusion = await asyncio.to_thread(
                fuse_emotions,
                [text_emotion, speech_emotion, face_emotion],
                {
                    'recent_dialogue': state.recent_dialogue,
                    'previous_fusion': state.previous_fusion or {},
                },
            )
            state.previous_fusion = final_fusion
            await websocket.send_json(event_payload('emotion.update', turn_id, emotion=final_fusion, modalities={
                'text': text_emotion,
                'speech': speech_emotion,
                'face': face_emotion,
                'fusion': final_fusion,
            }, meta={**meta, 'stage': 'final-with-speech'}))
        except Exception:
            pass

        public_api_base = os.getenv('PUBLIC_API_BASE_URL', 'http://127.0.0.1:5000').rstrip('/')
        tts = await asyncio.to_thread(
            synthesize_speech,
            dialogue.get('response', ''),
            dialogue.get('tts_emotion', fused_emotion.get('emotion', '平静')),
            settings,
            public_api_base,
        )
        await websocket.send_json(event_payload('tts.ready', turn_id, tts=tts, audio_url=tts.get('audio_url', '')))
    except Exception as exc:
        await websocket.send_json(error_payload(f'实时回合处理失败: {exc}', turn_id))
    finally:
        cleanup_audio_path(audio_path)


def decode_data_url(value: str) -> bytes:
    if not value:
        return b''
    if ',' in value:
        value = value.split(',', 1)[1]
    return base64.b64decode(value)


def build_pending_speech_emotion() -> dict:
    return {
        'source': 'speech',
        'emotion': '平静',
        'confidence': 0.25,
        'reliability': 0.12,
        'available': False,
        'distribution': {'开心': 0.14, '难过': 0.12, '疲惫': 0.12, '感激': 0.12, '平静': 0.5},
        'tags': ['语音情绪后台分析中'],
        'evidence': ['fast-preview-speech-pending'],
    }
