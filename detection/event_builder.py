import uuid
from datetime import datetime
from typing import Dict, Optional

try:
    from detection.session_manager import SessionManager
except ModuleNotFoundError:
    from session_manager import SessionManager


class EventBuilder:
    """Build events that conform to the retail analytics event schema."""

    def __init__(
        self,
        store_id: str,
        camera_id: str,
        session_manager: SessionManager,
    ) -> None:
        self.store_id = store_id
        self.camera_id = camera_id
        self.session_manager = session_manager

    def build_event(
        self,
        event_type: str,
        visitor_id: Optional[str] = None,
        zone_id: Optional[str] = None,
        confidence: Optional[float] = None,
        dwell_ms: Optional[int] = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        visitor_id_value = visitor_id or ""
        session_seq = self.session_manager.get_session_sequence(visitor_id_value) or 0
        is_staff = False
        if visitor_id_value:
            session = self.session_manager.get_session(visitor_id_value)
            is_staff = bool(session.get("is_staff", False)) if session is not None else False

        event: Dict[str, object] = {
            "event_id": str(uuid.uuid4()),
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "visitor_id": visitor_id_value,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "zone_id": zone_id or "",
            "dwell_ms": int(dwell_ms) if dwell_ms is not None else 0,
            "is_staff": is_staff,
            "confidence": float(confidence) if confidence is not None else 0.0,
            "metadata": {
                "queue_depth": None,
                "sku_zone": None,
                "session_seq": session_seq,
            },
        }

        if metadata:
            event["metadata"].update(metadata)

        return event
