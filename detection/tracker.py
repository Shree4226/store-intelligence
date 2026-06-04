"""
Retail store person tracking using YOLOv8 and ByteTrack.

This module processes an entry camera video, tracks people with persistent IDs,
annotates bounding boxes with ID and confidence, and writes the tracked video.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Set

ULTRALYTICS_CONFIG_DIR = Path("generated/ultralytics").resolve()
ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))

import cv2
import ultralytics
from ultralytics import YOLO


# Configuration
FRAME_SKIP = 5
INPUT_WIDTH = 640
CONFIDENCE_THRESHOLD = 0.35


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PersonTracker:
    """Person tracking class for retail analytics."""

    PERSON_CLASS_ID = 0
    DEFAULT_MODEL = "yolov8n.pt"
    DEVICE = "cpu"

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL,
        confidence_threshold: float = CONFIDENCE_THRESHOLD
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model: Optional[YOLO] = None
        self.tracker_config = self._resolve_tracker_config()
        self.unique_track_ids: Set[int] = set()
        self.active_track_ids: Set[int] = set()
        self.load_model()

    def _resolve_tracker_config(self) -> str:
        """Resolve the ByteTrack YAML configuration path from the Ultralytics package."""
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

    def draw_tracks(
        self,
        frame: 'cv2.Mat',
        results: 'ultralytics.engine.results.Results',
        frame_number: int,
        scale_factor: float = 1.0
    ) -> 'cv2.Mat':
        """Draw tracked person boxes, IDs, and confidence on the output frame."""
        annotated = frame.copy()

        box_color = (0, 255, 0)
        text_color = (255, 255, 255)
        id_color = (0, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2

        self.active_track_ids.clear()

        if results is not None and getattr(results, 'boxes', None) is not None and len(results.boxes) > 0:
            for box in results.boxes:
                # Only keep person detections
                cls_value = box.cls[0] if getattr(box, 'cls', None) is not None else None
                if cls_value is None or int(cls_value) != self.PERSON_CLASS_ID:
                    continue

                xyxy = getattr(box, 'xyxy', None)
                if xyxy is None or len(xyxy) == 0:
                    continue
                x1, y1, x2, y2 = xyxy[0].cpu().numpy().astype(int)
                x1 = int(x1 * scale_factor)
                y1 = int(y1 * scale_factor)
                x2 = int(x2 * scale_factor)
                y2 = int(y2 * scale_factor)

                conf_value = box.conf[0] if getattr(box, 'conf', None) is not None else None
                confidence = float(conf_value) if conf_value is not None else 0.0
                id_value = box.id[0] if getattr(box, 'id', None) is not None else None
                track_id = int(id_value) if id_value is not None else None

                if track_id is not None:
                    self.unique_track_ids.add(track_id)
                    self.active_track_ids.add(track_id)

                label = f"ID:{track_id if track_id is not None else 'NA'} {confidence:.2f}"

                cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(
                    annotated,
                    label,
                    (x1, max(y1 - 10, 20)),
                    font,
                    font_scale,
                    id_color,
                    thickness
                )

        # Draw diagnostics on frame
        stats_text = (
            f"Frame: {frame_number} | Active: {len(self.active_track_ids)} "
            f"| Unique IDs: {len(self.unique_track_ids)}"
        )
        cv2.putText(
            annotated,
            stats_text,
            (10, 30),
            font,
            font_scale,
            text_color,
            thickness
        )

        return annotated

    def process_video(
        self,
        input_video_path: str,
        output_video_path: str,
        skip_frames: int = FRAME_SKIP
    ) -> bool:
        """Process the video and apply person tracking frame by frame."""
        if not os.path.exists(input_video_path):
            error_msg = f"Input video not found: {input_video_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if self.model is None:
            error_msg = "Model not loaded. Cannot process video."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        output_dir = os.path.dirname(output_video_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")

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
            raise IOError(f"Failed to create output video writer for: {output_video_path}")

        target_width = min(INPUT_WIDTH, frame_width)
        target_height = int(frame_height * (target_width / frame_width))
        frames_to_process = (total_frames + skip_frames - 1) // skip_frames if total_frames > 0 else 0

        frame_number = 0
        processed_frames = 0
        start_time = time.time()

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
                interpolation=cv2.INTER_LINEAR
            )
            scale_factor = frame_width / float(target_width)

            try:
                results_generator = self.model.track(
                    source=resized_frame,
                    stream=True,
                    tracker=self.tracker_config,
                    persist=True,
                    classes=[self.PERSON_CLASS_ID],
                    conf=self.confidence_threshold,
                    verbose=False
                )
                results = next(results_generator)
            except StopIteration:
                results = None
            except Exception as e:
                logger.warning(f"Tracking failed on frame {frame_number}: {e}")
                results = None

            annotated_frame = self.draw_tracks(
                frame,
                results if results is not None else None,
                frame_number,
                scale_factor=scale_factor
            )
            writer.write(annotated_frame)

            if processed_frames % 100 == 0 or processed_frames == frames_to_process:
                elapsed = max(time.time() - start_time, 1e-6)
                fps_processed = processed_frames / elapsed
                remaining = max(frames_to_process - processed_frames, 0)
                eta = remaining / fps_processed if fps_processed else 0.0
                logger.info(
                    f"Frame {frame_number}: Active={len(self.active_track_ids)} | "
                    f"Unique IDs={len(self.unique_track_ids)} | "
                    f"Processed={processed_frames}/{frames_to_process} | "
                    f"FPS={fps_processed:.2f} | ETA={eta:.1f}s"
                )

        cap.release()
        writer.release()

        elapsed_total = max(time.time() - start_time, 1e-6)
        logger.info("Tracking complete")
        logger.info(f"Total frames read: {frame_number}")
        logger.info(f"Total frames processed: {processed_frames}")
        logger.info(f"Total unique visitors tracked: {len(self.unique_track_ids)}")
        logger.info(f"Output written to: {output_video_path}")
        logger.info(f"Average processed FPS: {processed_frames / elapsed_total:.2f}")

        return True


def main():
    input_video = "data/stores/store_1/videos/CAM 3 - entry.mp4"
    output_video = "generated/debug/store1_entry_tracking.mp4"

    logger.info("Starting PersonTracker pipeline")

    try:
        tracker = PersonTracker()
        tracker.process_video(
            input_video_path=input_video,
            output_video_path=output_video,
            skip_frames=FRAME_SKIP
        )
        logger.info("Person tracking finished successfully")
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
    except IOError as e:
        logger.error(f"I/O error: {e}")
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
