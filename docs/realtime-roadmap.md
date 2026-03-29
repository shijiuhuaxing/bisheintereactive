# Realtime Upgrade Roadmap

## Target

Build a low-latency interaction loop for:

1. continuous face emotion perception
2. short-turn dialogue generation
3. low-latency emotional speech generation

## Current Stage

- Face modality: local camera polling + backend model inference
- Speech recognition: stable mock fallback for demo reliability
- Dialogue generation: short emotional response generation
- TTS: Qwen3-TTS realtime API, currently collected then saved as WAV

## Realtime Architecture

### Frontend

- Keep camera stream alive during realtime monitoring
- Sample one frame every 1.0-1.5 seconds for face emotion refresh
- Start TTS pre-generation immediately after response text is available
- Play cached audio when user clicks play

### Backend

- Face route remains lightweight and stateless
- Dialogue route should keep responses short for low latency
- TTS route should support two modes:
  - buffered file output (current stable mode)
  - future streaming chunk forwarding mode

## Next Upgrades

1. replace mock ASR with streaming ASR or chunk ASR
2. add rolling temporal smoothing for face emotion history
3. replace buffered TTS playback with streaming playback
4. unify modalities in a session-level state manager
