"""
Entry event generator for retail analytics using YOLOv8 + ByteTrack.

This module processes a store entry camera feed, tracks people, detects
entry and exit events using a doorway polygon ROI, and writes event records to JSONL.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import ultralytics
from ultralytics import YOLO
from session_manager import SessionManager
from zone_manager import ZoneManager


# Configuration
ENTRY_POLYGON: Tuple[Tuple[int, int], ...] = (
    (930,170),
    (1250,170),
    (1360,560),
    (850,560)
)
EVENT_OUTPUT_PATH = "generated/events/store1_entry_events.jsonl"
INPUT_VIDEO_PATH = "data/stores/store_1/videos/CAM 3 - entry.mp4"
OUTPUT_VIDEO_PATH = "generated/debug/store1_entry_tracking.mp4"
FRAME_SKIP = 5
INPUT_WIDTH = 640
CONFIDENCE_THRESHOLD = 0.35
CAMERA_ID = "CAM3"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EntryEventGenerator:
    """Generate entry and exit events from tracked people crossing a line."""

    DEFAULT_MODEL = "yolov8n.pt"
    DEVICE = "cpu"

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL,
        entry_polygon: Tuple[Tuple[int, int], ...] = ENTRY_POLYGON,
        event_output_path: str = EVENT_OUTPUT_PATH,
    ):
        self.model_path = model_path
        self.entry_polygon = entry_polygon
        self.event_output_path = Path(event_output_path)
        self.event_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.model: Optional[YOLO] = None
        self.tracker_config = self._resolve_tracker_config()
        self.track_history: Dict[int, Dict[str, object]] = {}
        self.session_manager = SessionManager()
        self.session_manager.load_sessions()
        self.zone_manager = ZoneManager()
        self.entry_count = 0
        self.exit_count = 0
        self.load_model()

    def _resolve_tracker_config(self) -> str:
        """Locate the ByteTrack YAML configuration file in the Ultralytics package."""
        base_dir = Path(ultralytics.__file__).resolve().parent
        config_path = base_dir / "cfg" / "trackers" / "bytetrack.yaml"
        if not config_path.exists():
            error_msg = f"ByteTrack config not found at {config_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        return str(config_path)

    def load_model(self) -> None:
        """Load the YOLOv8 model and move it to CPU."""
        try:
            logger.info(f"Loading YOLOv8 model: {self.model_path}")
            self.model = YOLO(self.model_path)
            self.model.to(self.DEVICE)
            logger.info(f"Model loaded successfully on device: {self.DEVICE}")
        except Exception as e:
            error_msg = f"Unable to load model '{self.model_path}': {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    @staticmethod
    def is_inside_polygon(point: Tuple[float, float], polygon: Tuple[Tuple[int, int], ...]) -> bool:
        """Return whether a point is inside or on the edge of a polygon."""
        contour = np.array(polygon, dtype=np.int32)
        return cv2.pointPolygonTest(contour, point, False) >= 0

    @staticmethod
    def _centroid(box, scale_factor: float = 1.0) -> Optional[Tuple[float, float]]:
        """Return the centroid of a bounding box in original frame coordinates."""
        xyxy = getattr(box, "xyxy", None)
        if xyxy is None or len(xyxy) == 0:
            return None
        coords = xyxy[0].cpu().numpy().astype(float)
        x1, y1, x2, y2 = coords
        return (((x1 + x2) / 2.0) * scale_factor, ((y1 + y2) / 2.0) * scale_factor)

    def _polygon_centroid(self) -> Tuple[float, float]:
        """Compute the approximate center of the entry polygon."""
        xs = [p[0] for p in self.entry_polygon]
        ys = [p[1] for p in self.entry_polygon]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _movement_vector(self, prev: Tuple[float, float], curr: Tuple[float, float]) -> Tuple[float, float]:
        return (curr[0] - prev[0], curr[1] - prev[1])

    def _dot(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return a[0] * b[0] + a[1] * b[1]

    def _movement_toward_interior(
        self,
        prev: Tuple[float, float],
        curr: Tuple[float, float],
    ) -> bool:
        store_center = self._polygon_centroid()
        move_vec = self._movement_vector(prev, curr)
        target_vec = self._movement_vector(prev, store_center)
        return self._dot(move_vec, target_vec) > 0

    def _movement_away_from_interior(
        self,
        prev: Tuple[float, float],
        curr: Tuple[float, float],
    ) -> bool:
        store_center = self._polygon_centroid()
        move_vec = self._movement_vector(prev, curr)
        away_vec = self._movement_vector(curr, store_center)
        return self._dot(move_vec, away_vec) > 0

    def _event_payload(
        self,
        event_type: str,
        track_id: int,
        visitor_id: Optional[str] = None,
        zone_id: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, object]:
        """Build an event payload for JSONL output."""
        payload: Dict[str, object] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "track_id": track_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "camera_id": CAMERA_ID,
        }
        if visitor_id is not None:
            payload["visitor_id"] = visitor_id
        if zone_id is not None:
            payload["zone_id"] = zone_id
        if confidence is not None:
            payload["confidence"] = confidence
        return payload

    def _update_track_history(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        inside: bool,
        current_zone: Optional[str],
    ) -> Dict[str, object]:
        previous = self.track_history.get(track_id, {})
        prev_inside = previous.get("current_inside", False)
        previous_zone = previous.get("current_zone")
        same_zone = current_zone is not None and previous_zone == current_zone
        zone_enter_time = previous.get("zone_enter_time")
        dwell_count = previous.get("dwell_count", 0)

        if not same_zone:
            zone_enter_time = time.time() if current_zone is not None else None
            dwell_count = 0

        history = {
            "previous_centroid": previous.get("current_centroid", centroid),
            "current_centroid": centroid,
            "previous_inside": prev_inside,
            "current_inside": inside,
            "previous_zone": previous_zone,
            "current_zone": current_zone,
            "zone_enter_time": zone_enter_time,
            "dwell_count": dwell_count,
            "entry_streak": previous.get("entry_streak", 0),
            "exit_streak": previous.get("exit_streak", 0),
            "entry_candidate": previous.get("entry_candidate", False),
            "exit_candidate": previous.get("exit_candidate", False),
            "last_event": previous.get("last_event"),
        }

        if not prev_inside and inside:
            history["entry_candidate"] = True
            history["entry_streak"] = 1
        elif inside and history["entry_candidate"]:
            if self._movement_toward_interior(history["previous_centroid"], history["current_centroid"]):
                history["entry_streak"] += 1
            else:
                history["entry_candidate"] = False
                history["entry_streak"] = 0
        else:
            history["entry_candidate"] = False
            history["entry_streak"] = 0

        if prev_inside and not inside:
            history["exit_candidate"] = True
            history["exit_streak"] = 1
        elif not inside and history["exit_candidate"]:
            if self._movement_away_from_interior(history["previous_centroid"], history["current_centroid"]):
                history["exit_streak"] += 1
            else:
                history["exit_candidate"] = False
                history["exit_streak"] = 0
        else:
            if inside:
                history["exit_candidate"] = False
            history["exit_streak"] = 0

        return history

    def _should_generate_dwell(self, history: Dict[str, object]) -> Optional[int]:
        if history["current_zone"] is None or history["zone_enter_time"] is None:
            return None

        elapsed_ms = int((time.time() - history["zone_enter_time"]) * 1000)
        next_count = elapsed_ms // 30000
        if next_count > history["dwell_count"]:
            return elapsed_ms
        return None

    def _write_event(self, event: Dict[str, object]) -> None:
        """Append a single event record to the JSONL file."""
        with self.event_output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _should_generate_entry(self, history: Dict[str, object]) -> bool:
        return (
            history["entry_candidate"]
            and history["entry_streak"] >= 3
            and history["last_event"] != "entry"
        )

    def _should_generate_exit(self, history: Dict[str, object]) -> bool:
        return (
            history["exit_candidate"]
            and history["exit_streak"] >= 3
            and history["last_event"] != "exit"
        )

    def _process_track(
        self,
        box,
        frame_number: int,
        scale_factor: float,
        events: List[Dict[str, object]],
    ) -> Optional[str]:
        """Process a single tracked box and generate polygon-based entry/exit events."""
        track_id = None
        if hasattr(box, "id") and getattr(box, "id") is not None and len(box.id) > 0:
            track_id = int(box.id[0])
        if track_id is None:
            return None

        centroid = self._centroid(box, scale_factor=scale_factor)
        if centroid is None:
            return None

        inside = self.is_inside_polygon(centroid, ENTRY_POLYGON)
        current_zone = self.zone_manager.get_current_zone((int(centroid[0]), int(centroid[1])))
        history = self._update_track_history(track_id, centroid, inside, current_zone)

        direction = None
        zone_confidence = (
            float(box.conf[0])
            if hasattr(box, "conf") and getattr(box, "conf") is not None and len(box.conf) > 0
            else 0.0
        )

        if (
            history["previous_zone"] is not None
            and history["previous_zone"] != history["current_zone"]
        ):
            visitor_id = self.session_manager.get_visitor_id(track_id)
            if visitor_id is None:
                visitor_id = self.session_manager.create_entry_session(track_id)
            event = self._event_payload(
                "ZONE_EXIT",
                track_id,
                visitor_id,
                zone_id=history["previous_zone"],
                confidence=zone_confidence,
            )
            self._write_event(event)
            events.append(event)

        if history["previous_zone"] != history["current_zone"] and history["current_zone"] is not None:
            visitor_id = self.session_manager.get_visitor_id(track_id)
            if visitor_id is None:
                visitor_id = self.session_manager.create_entry_session(track_id)
            event = self._event_payload(
                "ZONE_ENTER",
                track_id,
                visitor_id,
                zone_id=history["current_zone"],
                confidence=zone_confidence,
            )
            self._write_event(event)
            events.append(event)

        dwell_ms = self._should_generate_dwell(history)
        if dwell_ms is not None:
            visitor_id = self.session_manager.get_visitor_id(track_id)
            if visitor_id is None:
                visitor_id = self.session_manager.create_entry_session(track_id)
            event = self._event_payload(
                "ZONE_DWELL",
                track_id,
                visitor_id,
                zone_id=history["current_zone"],
                confidence=zone_confidence,
            )
            event["dwell_ms"] = dwell_ms
            self._write_event(event)
            history["dwell_count"] = int(dwell_ms // 30000)
            events.append(event)

        if self._should_generate_entry(history):
            visitor_id = self.session_manager.create_entry_session(track_id)
            event = self._event_payload("entry", track_id, visitor_id)
            self._write_event(event)
            self.session_manager.increment_event_count(visitor_id)
            self.entry_count += 1
            history["last_event"] = "entry"
            events.append(event)
            direction = "entry"
        elif self._should_generate_exit(history):
            visitor_id = self.session_manager.get_visitor_id(track_id)
            event = self._event_payload("exit", track_id, visitor_id)
            self._write_event(event)
            if visitor_id is not None:
                self.session_manager.increment_event_count(visitor_id)
            self.session_manager.close_session(track_id)
            self.exit_count += 1
            history["last_event"] = "exit"
            events.append(event)
            direction = "exit"

        self.track_history[track_id] = history
        return direction

    def draw_events(
        self,
        frame: "cv2.Mat",
        results,
        frame_number: int,
        directions: Dict[int, str],
        scale_factor: float = 1.0,
    ) -> "cv2.Mat":
        """Draw the entry polygon, tracked box IDs, centroids, and state on the frame."""
        annotated = frame.copy()
        polygon_color = (0, 0, 255)
        box_color = (0, 255, 0)
        text_color = (255, 255, 255)
        direction_color = (0, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2

        contour = np.array(self.entry_polygon, dtype=np.int32)
        cv2.polylines(annotated, [contour], isClosed=True, color=polygon_color, thickness=3)
        cv2.putText(
            annotated,
            "ENTRY AREA",
            (self.entry_polygon[0][0] + 10, self.entry_polygon[0][1] - 10),
            font,
            font_scale,
            polygon_color,
            thickness,
        )

        if results is not None and getattr(results, "boxes", None) is not None:
            for box in results.boxes:
                if getattr(box, "id", None) is None or len(box.id) == 0:
                    continue
                track_id = int(box.id[0])
                confidence = float(box.conf[0]) if getattr(box, "conf", None) is not None and len(box.conf) > 0 else 0.0
                xyxy = getattr(box, "xyxy", None)
                if xyxy is None or len(xyxy) == 0:
                    continue
                x1b, y1b, x2b, y2b = xyxy[0].cpu().numpy().astype(float)
                x1b = int(x1b * scale_factor)
                y1b = int(y1b * scale_factor)
                x2b = int(x2b * scale_factor)
                y2b = int(y2b * scale_factor)
                centroid = ((x1b + x2b) / 2, (y1b + y2b) / 2)
                history = self.track_history.get(track_id, {})
                inside_state = "INSIDE" if history.get("current_inside", False) else "OUTSIDE"

                cv2.rectangle(annotated, (x1b, y1b), (x2b, y2b), box_color, 2)
                cv2.circle(annotated, (int(centroid[0]), int(centroid[1])), 4, (255, 0, 0), -1)
                zone_id = history.get("current_zone")
                zone_name = self.zone_manager.get_zone_name(zone_id) if zone_id else "UNKNOWN"
                cv2.putText(
                    annotated,
                    f"ID:{track_id}",
                    (x1b, y1b - 40),
                    font,
                    font_scale,
                    text_color,
                    thickness,
                )
                cv2.putText(
                    annotated,
                    f"ZONE:{zone_name}",
                    (x1b, y1b - 15),
                    font,
                    font_scale,
                    text_color,
                    thickness,
                )
                cv2.putText(
                    annotated,
                    f"C:{int(centroid[0])},{int(centroid[1])}",
                    (x1b, y2b + 20),
                    font,
                    0.5,
                    text_color,
                    1,
                )
                cv2.putText(
                    annotated,
                    f"{inside_state} {directions.get(track_id, '')}",
                    (x1b, min(y2b + 40, annotated.shape[0] - 10)),
                    font,
                    font_scale,
                    direction_color,
                    thickness,
                )

        summary = f"Frame {frame_number} | Entries {self.entry_count} | Exits {self.exit_count}"
        cv2.putText(
            annotated,
            summary,
            (10, annotated.shape[0] - 20),
            font,
            font_scale,
            text_color,
            thickness,
        )

        return annotated

    def process_video(
        self,
        input_video_path: str = INPUT_VIDEO_PATH,
        output_video_path: str = OUTPUT_VIDEO_PATH,
        skip_frames: int = FRAME_SKIP,
    ) -> bool:
        """Process the entry video, track people, and detect crossing events."""
        if not os.path.exists(input_video_path):
            error_msg = f"Input video not found: {input_video_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if self.model is None:
            raise RuntimeError("Model not loaded. Cannot process video.")

        output_dir = Path(output_video_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        writer = None
        frame_number = 0
        processed_frames = 0
        start_time = time.time()

        with self.event_output_path.open("w", encoding="utf-8") as _:  # reset event file
            pass

        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            raise IOError(f"Failed to open video: {input_video_path}")

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        logger.info(
            f"Video opened: {input_video_path} | Resolution: {frame_width}x{frame_height} | "
            f"FPS: {fps:.2f} | Total frames: {total_frames}"
        )

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))
        if not writer.isOpened():
            raise IOError(f"Failed to create output video writer: {output_video_path}")

        target_width = min(INPUT_WIDTH, frame_width)
        target_height = int(frame_height * (target_width / frame_width))

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_number += 1

            if frame_number % skip_frames != 0:
                writer.write(frame)
                continue

            processed_frames += 1
            resized_frame = cv2.resize(
                frame,
                (target_width, target_height),
                interpolation=cv2.INTER_LINEAR,
            )
            scale_factor = frame_width / float(target_width)

            directions: Dict[int, str] = {}
            events: List[Dict[str, object]] = []
            try:
                results_gen = self.model.track(
                    source=resized_frame,
                    stream=True,
                    tracker=self.tracker_config,
                    persist=True,
                    classes=[0],
                    conf=CONFIDENCE_THRESHOLD,
                    verbose=False,
                )
                results = next(results_gen)
            except StopIteration:
                results = None
            except Exception as exc:
                logger.warning(f"Tracking failed on frame {frame_number}: {exc}")
                results = None

            if results is not None and getattr(results, "boxes", None) is not None:
                for box in results.boxes:
                    if getattr(box, "id", None) is None:
                        continue
                    direction = self._process_track(box, frame_number, scale_factor, events)
                    if direction is not None:
                        track_id = int(box.id[0])
                        directions[track_id] = direction

            annotated = self.draw_events(frame, results, frame_number, directions, scale_factor=scale_factor)
            writer.write(annotated)

            if processed_frames % 100 == 0:
                elapsed = max(time.time() - start_time, 1e-6)
                fps_processed = processed_frames / elapsed
                logger.info(
                    f"Frame {frame_number} | Processed {processed_frames} | "
                    f"Entries {self.entry_count} | Exits {self.exit_count} | "
                    f"FPS {fps_processed:.2f}"
                )

        cap.release()
        writer.release()
        self.session_manager.save_sessions()

        logger.info("Event generation completed")
        logger.info(f"Total frames read: {frame_number}")
        logger.info(f"Total entry events: {self.entry_count}")
        logger.info(f"Total exit events: {self.exit_count}")
        logger.info(f"Events saved to: {self.event_output_path}")
        logger.info(f"Tracked video saved to: {output_video_path}")
        logger.info(f"Sessions saved to: {SESSION_OUTPUT_PATH}")

        return True


def main() -> None:
    generator = EntryEventGenerator()
    generator.process_video()


if __name__ == "__main__":
    main()
