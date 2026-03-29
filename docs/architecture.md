# System Architecture

## Goal

Build a graduation-project-ready virtual companion system with four core capabilities:

1. Multi-modal emotion perception
2. Emotion-guided dialogue generation
3. Speech synthesis and avatar feedback
4. Real-time interactive demo and evaluation support

## Layered Design

### Frontend

- Audio recording and later video capture
- Display of ASR result, per-modality emotion result, fused emotion, and AI response
- Avatar state update and playback controls

### Backend API

- Route layer for HTTP endpoints
- Service layer for ASR, emotion recognition, fusion, dialogue, and TTS
- Schema layer for normalized response payloads

### Model Layer

- Text emotion recognition
- Speech emotion recognition
- Face emotion recognition
- Fusion strategy and LLM prompt strategy

### Data and Experiment Layer

- Sample data for debugging
- Evaluation output for metrics and case studies
- Thesis records and weekly notes in `docs/`

## Recommended Iteration Order

1. Finish ASR + text emotion + dialogue + TTS closed loop
2. Add speech emotion recognition
3. Add face emotion recognition
4. Add confidence-aware fusion
5. Add real-time avatar feedback and experiments

## Key Core Modules

- `backend/app/services/asr_service.py`
- `backend/app/services/emotion/text_emotion.py`
- `backend/app/services/emotion/speech_emotion.py`
- `backend/app/services/emotion/face_emotion.py`
- `backend/app/services/fusion_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/services/tts_service.py`

## Thesis Mapping

- System design chapter: directory structure, architecture, API, interaction flow
- Method chapter: multi-modal fusion and emotion-guided generation
- Experiment chapter: model comparison, ablation, latency, and case analysis
