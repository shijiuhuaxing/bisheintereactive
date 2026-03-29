# Multi-Modal Virtual Companion

## Project Overview

This repository contains the graduation project scaffold for a multi-modal virtual companion system.
The current codebase is organized for staged development: frontend interaction, backend services, model access, experiment records, and thesis materials.

## Directory Structure

```text
.
|-- frontend/              # Static demo frontend
|-- backend/               # Flask backend and service modules
|-- docs/                  # Architecture, API notes, thesis materials
|-- data/                  # Raw, processed, and evaluation data
|-- models/                # Model configs and checkpoints
|-- scripts/               # Startup and utility scripts
|-- logs/                  # Runtime logs
`-- outputs/               # Generated audio, reports, screenshots
```

## Quick Start

### Frontend

```bash
cd frontend
python -m http.server 8000
```

Open `http://localhost:8000`.

### Backend

```bash
python backend_example.py
```

Backend default address: `http://localhost:5000`

## Important Files

- `docs/architecture.md`: system architecture and development roadmap
- `docs/当前项目说明与使用指南.md`: current stack, usage, functions, and performance notes
- `docs/api.md`: ASR integration notes
- `docs/user-guide.md`: original demo usage guide
- `backend/app/main.py`: Flask app factory
- `frontend/static/js/api.js`: frontend API base configuration

## Current Status

- Frontend demo has been moved into `frontend/`
- Backend has been split into routes, services, and schemas under `backend/app/`
- Mock logic is preserved so the project can keep running before full model integration
- Local face modality now uses an ONNX FERPlus expression classifier for camera-frame inference

## DashScope ASR Setup

1. Copy `.env.example` to `.env`
2. Set `USE_MOCK_SERVICES=false`
3. Fill in `DASHSCOPE_API_KEY`
4. Restart the backend with `python backend_example.py`

Notes:

- The backend now sends uploaded audio to DashScope when mock mode is disabled
- The frontend uploads the recorded file using an extension inferred from the browser MIME type
- Browser recording is commonly `webm`; if DashScope rejects that format, add an audio conversion step on the backend

## Qwen3-TTS Setup

1. Copy `.env.example` to `.env`
2. Set `TTS_PROVIDER=qwen_dashscope`
3. Set `USE_MOCK_SERVICES=false`
4. Fill in `DASHSCOPE_API_KEY`
5. Restart backend with `python backend_example.py`

Suggested defaults:

```env
TTS_PROVIDER=qwen_dashscope
DASHSCOPE_TTS_MODEL=qwen3-tts-instruct-flash-realtime
DASHSCOPE_TTS_VOICE=Cherry
DASHSCOPE_TTS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
```

If you only want to enable real TTS while keeping speech recognition stable, set:

```env
ASR_PROVIDER=mock
```

Current implementation notes:

- Backend `tts_service.py` uses a pluggable provider design
- `mock` provider is preserved as fallback
- `qwen_dashscope` provider uses Qwen3-TTS realtime API and saves generated PCM as local WAV files under `outputs/audios/`

## Next Development Focus

1. Replace mock ASR, LLM, and TTS with real services
2. Add video emotion recognition and multi-modal fusion
3. Complete evaluation scripts and thesis experiment records
