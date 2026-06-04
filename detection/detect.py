"""
Person Detection Module using YOLOv8

This module provides a production-ready implementation for detecting people
in video files using the YOLOv8 nano model from Ultralytics. It processes
video frames, draws bounding boxes with confidence scores, and saves the
annotated output.

Author: Computer Vision Team
Date: 2026-06-03
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

ULTRALYTICS_CONFIG_DIR = Path("generated/ultralytics").resolve()
ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))

import cv2
from ultralytics import YOLO


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration variables
FRAME_SKIP = 5
INPUT_WIDTH = 640
CONFIDENCE_THRESHOLD = 0.35


class PersonDetector:
    """
    A production-ready person detection class using YOLOv8.
    
    This class handles loading the YOLOv8 model, processing video files,
    detecting people, and saving annotated output videos.
    
    Attributes:
        model_path (str): Path to the YOLOv8 model weights file
        model (YOLO): The loaded YOLO model instance
        person_class_id (int): COCO class ID for person (always 0)
        confidence_threshold (float): Minimum confidence for detections
    """
    
    PERSON_CLASS_ID = 0  # COCO class 0 is 'person'
    DEFAULT_MODEL = "yolov8n.pt"  # YOLOv8 nano model
    DEVICE = "cpu"
    
    def __init__(
        self,
        model_path: str = DEFAULT_MODEL,
        confidence_threshold: float = CONFIDENCE_THRESHOLD
    ):
        """
        Initialize the PersonDetector.
        
        Args:
            model_path (str): Path to the YOLOv8 model file. Defaults to yolov8n.pt
            confidence_threshold (float): Minimum confidence score for detections.
                                         Defaults to 0.5
        
        Raises:
            ValueError: If model_path is invalid or model fails to load
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        
        # Load the model during initialization
        self.load_model()
    
    def load_model(self) -> None:
        """
        Load the YOLOv8 model from the specified path.
        
        The model is loaded with device auto-detection (GPU if available).
        
        Raises:
            FileNotFoundError: If the model file doesn't exist
            RuntimeError: If model loading fails
        """
        try:
            logger.info(f"Loading YOLOv8 model from: {self.model_path}")
            logger.info("Forcing CPU-only inference to optimize resource usage")
            
            # Initialize YOLO model and move it to CPU explicitly
            self.model = YOLO(self.model_path)
            self.model.to(self.DEVICE)
            
            logger.info(f"Model loaded successfully: {self.model_path}")
            logger.info(f"Using device: {self.DEVICE}")
            
        except Exception as e:
            error_msg = f"Failed to load model '{self.model_path}': {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def draw_detections(
        self,
        frame: 'cv2.Mat',
        results: 'YOLO.Results',
        frame_number: int,
        scale_factor: float = 1.0
    ) -> 'cv2.Mat':
        """
        Draw bounding boxes and confidence scores on the frame.
        
        This method processes detections and annotates the frame with:
        - Green bounding boxes for each detected person
        - Confidence scores displayed above each box
        - Current frame number in the top-left corner
        
        Args:
            frame (cv2.Mat): The video frame to annotate
            results (YOLO.Results): Detection results from the model
            frame_number (int): Current frame number for display
        
        Returns:
            cv2.Mat: Annotated frame with bounding boxes and information
        """
        annotated_frame = frame.copy()
        
        # Define colors and fonts
        box_color = (0, 255, 0)  # Green in BGR
        text_color = (0, 0, 255)  # Red in BGR
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        
        # Extract detections from results
        if results[0].boxes is not None:
            boxes = results[0].boxes
            
            # Iterate through each detection
            for box in boxes:
                # Get bounding box coordinates and scale them to the original frame
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                x1 = int(x1 * scale_factor)
                y1 = int(y1 * scale_factor)
                x2 = int(x2 * scale_factor)
                y2 = int(y2 * scale_factor)
                
                # Get confidence score
                confidence = float(box.conf[0])
                
                # Draw bounding box
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2)
                
                # Prepare confidence text
                confidence_text = f"{confidence:.2f}"
                
                # Get text size for background
                text_size = cv2.getTextSize(
                    confidence_text, font, font_scale, font_thickness
                )[0]
                
                # Draw background rectangle for text
                text_x = x1
                text_y = y1 - 10
                bg_x1 = text_x - 5
                bg_y1 = text_y - text_size[1] - 5
                bg_x2 = text_x + text_size[0] + 5
                bg_y2 = text_y + 5
                
                cv2.rectangle(
                    annotated_frame,
                    (bg_x1, bg_y1),
                    (bg_x2, bg_y2),
                    box_color,
                    -1  # Fill the rectangle
                )
                
                # Draw confidence text
                cv2.putText(
                    annotated_frame,
                    confidence_text,
                    (text_x, text_y),
                    font,
                    font_scale,
                    (255, 255, 255),  # White text
                    font_thickness
                )
        
        # Draw frame number in top-left corner
        frame_text = f"Frame: {frame_number}"
        cv2.putText(
            annotated_frame,
            frame_text,
            (10, 30),
            font,
            font_scale,
            text_color,
            font_thickness
        )
        
        return annotated_frame
    
    def process_video(
        self,
        input_video_path: str,
        output_video_path: str,
        skip_frames: int = FRAME_SKIP
    ) -> bool:
        """
        Process a video file and detect people in each frame.
        
        This method:
        1. Opens the input video file
        2. Processes each frame with YOLO detection
        3. Filters detections to only include people (class 0)
        4. Draws bounding boxes and confidence scores
        5. Saves the annotated video
        
        Args:
            input_video_path (str): Path to the input video file
            output_video_path (str): Path where the output video will be saved
            skip_frames (int): Process every nth frame (1 = all frames). Defaults to 1
        
        Returns:
            bool: True if processing completed successfully, False otherwise
        
        Raises:
            FileNotFoundError: If input video file doesn't exist
            IOError: If output directory cannot be created
        """
        # Validate input video
        if not os.path.exists(input_video_path):
            error_msg = f"Input video not found: {input_video_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Ensure model is loaded
        if self.model is None:
            error_msg = "Model not loaded. Call load_model() first."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_video_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Created output directory: {output_dir}")
            except Exception as e:
                error_msg = f"Failed to create output directory: {str(e)}"
                logger.error(error_msg)
                raise IOError(error_msg) from e
        
        try:
            logger.info(f"Opening video: {input_video_path}")
            
            # Open input video
            cap = cv2.VideoCapture(input_video_path)
            if not cap.isOpened():
                raise IOError(f"Failed to open video: {input_video_path}")
            
            # Get video properties
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"Video properties - Resolution: {frame_width}x{frame_height}, "
                       f"FPS: {fps:.2f}, Total frames: {total_frames}")
            
            # Create video writer using original resolution for acceptable output quality
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))
            
            if not out.isOpened():
                raise IOError(f"Failed to open video writer for: {output_video_path}")
            
            logger.info(f"Writing output to: {output_video_path}")
            
            frame_count = 0
            processed_frames = 0
            start_time = time.time()
            target_width = min(INPUT_WIDTH, frame_width)
            target_height = int(frame_height * (target_width / frame_width))
            frames_to_process = (total_frames + skip_frames - 1) // skip_frames
            
            # Process each frame
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                frame_count += 1
                
                # Skip frames if requested; write skipped frames unmodified
                if frame_count % skip_frames != 0:
                    out.write(frame)
                    continue
                
                try:
                    # Resize frame for faster CPU inference while preserving aspect ratio
                    resized_frame = cv2.resize(
                        frame,
                        (target_width, target_height),
                        interpolation=cv2.INTER_LINEAR
                    )
                    scale_factor = frame_width / float(target_width)
                    
                    # Run YOLOv8 inference on resized frame
                    results = self.model(resized_frame, conf=self.confidence_threshold, verbose=False)
                    
                    # Filter detections to only person class (class 0)
                    if len(results[0].boxes) > 0:
                        person_boxes = results[0].boxes[results[0].boxes.cls == self.PERSON_CLASS_ID]
                        if len(person_boxes) > 0:
                            results[0].boxes = person_boxes
                        else:
                            results[0].boxes = None
                    
                    # Draw detections on the original frame using scaled coordinates
                    annotated_frame = self.draw_detections(
                        frame,
                        results,
                        frame_count,
                        scale_factor=scale_factor
                    )
                    
                    out.write(annotated_frame)
                    processed_frames += 1
                    
                    if processed_frames % 100 == 0 or processed_frames == frames_to_process:
                        elapsed = max(time.time() - start_time, 1e-6)
                        fps_processed = processed_frames / elapsed
                        remaining_items = max(frames_to_process - processed_frames, 0)
                        remaining_time = remaining_items / fps_processed
                        logger.info(
                            f"Processed frames: {processed_frames}/{frames_to_process}, "
                            f"Total frames: {total_frames}, FPS: {fps_processed:.2f}, "
                            f"ETA: {remaining_time:.1f}s"
                        )
                except Exception as e:
                    logger.warning(f"Error processing frame {frame_count}: {str(e)}")
                    out.write(frame)  # Write original frame on error
                    continue
            
            cap.release()
            out.release()
            
            elapsed_total = max(time.time() - start_time, 1e-6)
            final_fps = processed_frames / elapsed_total if processed_frames else 0.0
            logger.info("Video processing completed successfully!")
            logger.info(
                f"Total frames: {frame_count}, Processed frames: {processed_frames}, "
                f"Average FPS: {final_fps:.2f}, Output: {output_video_path}"
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Error during video processing: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e


def main():
    """
    Main execution function for direct script invocation.
    
    Sets up input/output paths and runs the person detection pipeline.
    """
    # Define paths
    input_video = "data/stores/store_1/videos/CAM 3 - entry.mp4"
    output_video = "generated/debug/store1_entry_detection.mp4"
    
    logger.info("=" * 60)
    logger.info("Starting Person Detection Pipeline")
    logger.info("=" * 60)
    
    try:
        # Create detector instance
        detector = PersonDetector(
            model_path=PersonDetector.DEFAULT_MODEL,
            confidence_threshold=CONFIDENCE_THRESHOLD
        )
        
        # Process video using CPU-optimized settings
        success = detector.process_video(
            input_video_path=input_video,
            output_video_path=output_video,
            skip_frames=FRAME_SKIP
        )
        
        if success:
            logger.info("=" * 60)
            logger.info("Pipeline completed successfully!")
            logger.info(f"Output saved to: {output_video}")
            logger.info("=" * 60)
        else:
            logger.error("Pipeline failed to complete")
            
    except FileNotFoundError as e:
        logger.error(f"File error: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
