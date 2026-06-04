from pathlib import Path

import cv2

VIDEO_PATH = Path("data/stores/store_1/videos/CAM 3 - entry.mp4")
OUTPUT_PATH = Path("generated/debug/frame_100.jpg")
FRAME_NUMBER = 100


def main() -> None:
    if not VIDEO_PATH.exists():
        print(f"Error: Video file not found: {VIDEO_PATH}")
        return

    cap = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap.isOpened():
        print(f"Error: Unable to open video: {VIDEO_PATH}")
        return

    target_index = FRAME_NUMBER - 1
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_index)
    ret, frame = cap.read()
    if not ret or frame is None:
        print(f"Error: Unable to read frame {FRAME_NUMBER} from video.")
        cap.release()
        return

    height, width = frame.shape[:2]
    print(f"Frame width: {width}")
    print(f"Frame height: {height}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(str(OUTPUT_PATH), frame)
    cap.release()

    if success:
        print(f"Saved frame {FRAME_NUMBER} to: {OUTPUT_PATH}")
    else:
        print(f"Error: Failed to save image to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
