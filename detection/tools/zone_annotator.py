import json
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

IMAGE_PATH = Path("data/stores/store_1/frame_sample.jpg")
OUTPUT_JSON_PATH = Path("generated/zones/skincare_zone.json")
ZONE_NAME = "SKINCARE"

points: List[Tuple[int, int]] = []


def draw_zone(image: cv2.Mat, points: List[Tuple[int, int]]) -> cv2.Mat:
    canvas = image.copy()
    if points:
        for idx, (x, y) in enumerate(points):
            cv2.circle(canvas, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(
                canvas,
                f"{idx + 1}: ({x}, {y})",
                (x + 8, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )

        if len(points) > 1:
            contour = np.array(points, dtype=np.int32)
            cv2.polylines(canvas, [contour], isClosed=False, color=(0, 0, 255), thickness=2)

    cv2.putText(
        canvas,
        "Left-click to add point | S=save | C=clear | Q=quit",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return canvas


def mouse_callback(event: int, x: int, y: int, flags: int, param: object) -> None:
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    points.append((x, y))
    print(f"Added point: ({x}, {y})")


def save_polygon(points: List[Tuple[int, int]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "zone_name": ZONE_NAME,
        "polygon": [[int(x), int(y)] for x, y in points],
    }
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    print(f"Saved polygon to: {output_path}")


def main() -> None:
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Image not found: {IMAGE_PATH}")

    image = cv2.imread(str(IMAGE_PATH))
    if image is None:
        raise ValueError(f"Unable to load image: {IMAGE_PATH}")

    window_name = "Zone Annotator"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, mouse_callback)

    while True:
        display_image = draw_zone(image, points)
        cv2.imshow(window_name, display_image)

        key = cv2.waitKey(20) & 0xFF
        if key == ord("q"):
            print("Quitting without saving.")
            break
        if key == ord("c"):
            points.clear()
            print("Cleared all points.")
        if key == ord("s"):
            if not points:
                print("No points to save.")
                continue
            save_polygon(points, OUTPUT_JSON_PATH)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
