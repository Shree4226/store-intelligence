import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SESSION_OUTPUT_PATH = Path("generated/events/sessions.json")


def _format_visitor_id(sequence: int) -> str:
    return f"VIS_{sequence:06d}"


class SessionManager:
    """Manage visitor sessions independently from ByteTrack track IDs."""

    def __init__(self) -> None:
        self.active_sessions: Dict[int, Dict[str, object]] = {}
        self.closed_sessions: List[Dict[str, object]] = []
        self._next_sequence: int = 1

    def _next_visitor_id(self) -> str:
        visitor_id = _format_visitor_id(self._next_sequence)
        self._next_sequence += 1
        return visitor_id

    def create_entry_session(self, track_id: int, entry_time: Optional[str] = None) -> str:
        """Create a new session for a track when an ENTRY event occurs."""
        if track_id in self.active_sessions:
            return self.active_sessions[track_id]["visitor_id"]

        visitor_id = self._next_visitor_id()
        entry_time = entry_time or datetime.utcnow().isoformat() + "Z"

        session = {
            "visitor_id": visitor_id,
            "track_id": track_id,
            "entry_time": entry_time,
            "exit_time": None,
            "event_count": 0,
            "sequence": self._next_sequence - 1,
            "status": "active",
            "is_staff": False,
            "purchase_made": False,
        }

        self.active_sessions[track_id] = session
        return visitor_id

    def restore_entry_session(
        self,
        track_id: int,
        visitor_id: str,
        entry_time: Optional[str] = None,
    ) -> str:
        """Restore a closed visitor session for re-entry using the original visitor ID."""
        if track_id in self.active_sessions:
            return self.active_sessions[track_id]["visitor_id"]

        existing = next(
            (session for session in self.closed_sessions if session["visitor_id"] == visitor_id),
            None,
        )
        entry_time = entry_time or datetime.utcnow().isoformat() + "Z"
        sequence = existing["sequence"] if existing is not None else self._next_sequence
        if existing is None:
            self._next_sequence += 1

        session = {
            "visitor_id": visitor_id,
            "track_id": track_id,
            "entry_time": entry_time,
            "exit_time": None,
            "event_count": existing["event_count"] if existing is not None else 0,
            "sequence": sequence,
            "status": "active",
            "is_staff": existing["is_staff"] if existing is not None else False,
            "purchase_made": existing["purchase_made"] if existing is not None else False,
        }

        self.active_sessions[track_id] = session
        return visitor_id

    def close_session(self, track_id: int, exit_time: Optional[str] = None) -> Optional[Dict[str, object]]:
        """Close the active session for a track when an EXIT event occurs."""
        session = self.active_sessions.pop(track_id, None)
        if session is None:
            return None

        exit_time = exit_time or datetime.utcnow().isoformat() + "Z"
        session["exit_time"] = exit_time
        session["status"] = "closed"
        self.closed_sessions.append(session)
        return session

    def get_visitor_id(self, track_id: int) -> Optional[str]:
        """Return the visitor ID for an active track ID, or None if not found."""
        session = self.active_sessions.get(track_id)
        if session is None:
            return None
        return session["visitor_id"]

    def mark_purchase(self, visitor_id: str) -> bool:
        """Mark that a visitor session has completed a purchase."""
        session = self.get_session(visitor_id)
        if session is None:
            return False
        session["purchase_made"] = True
        return True

    def has_purchase(self, visitor_id: str) -> bool:
        """Return whether a session has a purchase recorded."""
        session = self.get_session(visitor_id)
        return bool(session and session.get("purchase_made", False))

    def increment_event_count(self, visitor_id: str, amount: int = 1) -> Optional[int]:
        """Increment the event count for a visitor session."""
        all_sessions = list(self.active_sessions.values()) + self.closed_sessions
        for session in all_sessions:
            if session["visitor_id"] == visitor_id:
                session["event_count"] = int(session.get("event_count", 0)) + amount
                return session["event_count"]
        return None

    def get_active_session(self, track_id: int) -> Optional[Dict[str, object]]:
        return self.active_sessions.get(track_id)

    def get_session(self, visitor_id: str) -> Optional[Dict[str, object]]:
        all_sessions = list(self.active_sessions.values()) + self.closed_sessions
        return next((session for session in all_sessions if session["visitor_id"] == visitor_id), None)

    def set_staff(self, visitor_id: str, is_staff: bool = True) -> bool:
        session = self.get_session(visitor_id)
        if session is None:
            return False
        session["is_staff"] = is_staff
        return True

    def get_session_sequence(self, visitor_id: str) -> Optional[int]:
        """Return the numeric session sequence for a visitor ID."""
        all_sessions = list(self.active_sessions.values()) + self.closed_sessions
        for session in all_sessions:
            if session["visitor_id"] == visitor_id:
                return int(session.get("sequence", 0))
        return None

    def all_sessions(self) -> List[Dict[str, object]]:
        """Return all sessions, both active and closed."""
        return list(self.active_sessions.values()) + self.closed_sessions

    def save_sessions(self, file_path: Path = SESSION_OUTPUT_PATH) -> None:
        """Save all sessions to JSON file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.all_sessions()
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def load_sessions(self, file_path: Path = SESSION_OUTPUT_PATH) -> None:
        """Load sessions from JSON file, preserving next sequence number."""
        if not file_path.exists():
            return

        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        self.closed_sessions = [session for session in data if session.get("status") == "closed"]
        self.active_sessions = {
            session["track_id"]: session for session in data if session.get("status") == "active"
        }
        sequences = [int(session["sequence"]) for session in data if session.get("sequence") is not None]
        self._next_sequence = max(sequences, default=0) + 1


if __name__ == "__main__":
    manager = SessionManager()
    print("Starting session manager example")

    visit_a = manager.create_entry_session(track_id=101)
    print("Created", visit_a)

    manager.increment_event_count(visit_a)
    manager.increment_event_count(visit_a)

    visit_b = manager.create_entry_session(track_id=102)
    print("Created", visit_b)

    manager.close_session(track_id=101)
    manager.save_sessions()

    print("Visitor A sequence:", manager.get_session_sequence(visit_a))
    print("Visitor B track lookup:", manager.get_visitor_id(102))
    print("Saved sessions to", SESSION_OUTPUT_PATH)
