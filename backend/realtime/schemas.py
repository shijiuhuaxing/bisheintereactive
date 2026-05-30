from __future__ import annotations

from typing import Any


def event_payload(event_type: str, turn_id: str = '', **payload: Any) -> dict[str, Any]:
    data = {
        'type': event_type,
        'turn_id': turn_id,
    }
    data.update(payload)
    return data


def error_payload(message: str, turn_id: str = '') -> dict[str, Any]:
    return event_payload('error', turn_id, message=message)
