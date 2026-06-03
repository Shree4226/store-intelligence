import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

STORE_LAYOUT_PATH = Path("E:\store-intelligence\config\store_layout.json")
Point = Tuple[int, int]
Polygon = List[Point]


class ZoneManager:
    """Load store zones and determine whether points fall inside a zone."""

    def __init__(self, layout_path: Path = STORE_LAYOUT_PATH) -> None:
        self.layout_path = layout_path
        self.store_id: Optional[str] = None
        self.zones: List[Dict[str, Any]] = []
        self._load_layout()

    def _load_layout(self) -> None:
        if not self.layout_path.exists():
            raise FileNotFoundError(f"Zone layout not found: {self.layout_path}")

        with self.layout_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        self.store_id = data.get("store_id")
        self.zones = []
        for zone in data.get("zones", []):
            polygon = zone.get("polygon", [])
            if len(polygon) < 3:
                continue
            self.zones.append(
                {
                    "zone_id": zone.get("zone_id"),
                    "name": zone.get("name"),
                    "polygon": [(int(x), int(y)) for x, y in polygon],
                }
            )

    @staticmethod
    def is_inside_zone(point: Point, zone_polygon: Polygon) -> bool:
        """Return True if point is inside or on the boundary of the polygon."""
        contour = np.array(zone_polygon, dtype=np.int32)
        return cv2.pointPolygonTest(contour, point, False) >= 0

    def get_current_zone(self, point: Point) -> Optional[str]:
        """Return the zone_id of the first zone that contains the point, or None."""
        for zone in self.zones:
            if self.is_inside_zone(point, zone["polygon"]):
                return zone["zone_id"]
        return None

    def get_zone_name(self, zone_id: str) -> Optional[str]:
        """Return the zone name for a given zone_id."""
        for zone in self.zones:
            if zone["zone_id"] == zone_id:
                return zone["name"]
        return None


if __name__ == "__main__":
    import numpy as np

    manager = ZoneManager()
    print(f"Loaded store: {manager.store_id}")
    print(f"Loaded zones: {[zone['zone_id'] for zone in manager.zones]}")

    test_points = [
        (200, 200),
        (700, 200),
        (1300, 200),
        (200, 600),
        (700, 600),
        (1300, 600),
        (10, 10),
    ]

    for point in test_points:
        zone_id = manager.get_current_zone(point)
        zone_name = manager.get_zone_name(zone_id) if zone_id else None
        print(f"Point {point} -> zone_id={zone_id}, name={zone_name}")
