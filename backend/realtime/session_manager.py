from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class RealtimeSessionState:
    session_id: str
    created_at: float = field(default_factory=time)
    recent_dialogue: list[dict] = field(default_factory=list)
    latest_face: dict | None = None
    previous_fusion: dict | None = None

    def append_dialogue(self, user_text: str, assistant_text: str, emotion: str) -> None:
        self.recent_dialogue.append({
            'user': user_text,
            'assistant': assistant_text,
            'emotion': emotion,
        })
        self.recent_dialogue = self.recent_dialogue[-4:]


class RealtimeSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, RealtimeSessionState] = {}

    def get(self, session_id: str) -> RealtimeSessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = RealtimeSessionState(session_id=session_id)
        return self._sessions[session_id]

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


session_manager = RealtimeSessionManager()
