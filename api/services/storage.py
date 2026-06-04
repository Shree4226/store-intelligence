from typing import Any, Dict, Optional


class StorageUnavailableError(RuntimeError):
    """Raised when API state storage cannot be accessed."""


class InMemoryStorage:
    """Simple in-memory key/value storage for API state."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def all(self) -> Dict[str, Any]:
        return dict(self._data)

    def clear(self) -> None:
        self._data.clear()


storage = InMemoryStorage()
