import os
import sys
import cv2
import time
import yaml
import json
import shutil
import atexit
import threading
from pathlib import Path
from datetime import datetime

# --- Path Setup ---
# Calculate the project root directory (d:\StudyWorks\3.1\item1\SparkBox)
BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_DIR = BASE_DIR / "tasks"

# Add task directories to sys.path to allow imports
sys.path.append(str(TASKS_DIR / "img_input"))
sys.path.append(str(TASKS_DIR / "talk"))

# --- Imports from project modules ---
try:
    from detect import SquareDetector
    from voice2text import Voice2Text
    from vision_module import VisionAgent
    from mentor_module import SolutionAgent
    from image_module import ImageGenAgent
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure your project structure is correct.")
    sys.exit(1)

class SparkBoxApp:
    def __init__(self):
        self.running = True
        self.camera_id = 1  # Default camera
        self.cap = None
        
        # Paths
        self.logs_dir = BASE_DIR / "logs"
        self.temp_dir = self.logs_dir / "temp"
        self.asset_dir = BASE_DIR / "asset"
        self.config_dir = BASE_DIR / "config"
        
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Cleanup configuration
        atexit.register(self.cleanup_temp)
        
        # State
        self.is_processing_ai = False
        self.ai_status_message = "Ready"
        
        # Voice State
        self.is_recording = False
        self.last_b_press_time = 0
        self.voice_timeout = 0.4  # Seconds to wait before assuming key release
        
        # Load Configurations
        self.global_config = self._load_config(self.config_dir / "config.yaml")
        
        # Initialize Modules
        print("Initializing modules...")
        self._init_detector()
        self._init_voice()
        self._init_agents()
        print("Initialization complete.")

    def _load_config(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Failed to load config {path}: {e}")
            return {}

    def _init_detector(self):
        camera_config = self.asset_dir / "camera.yaml"
        if not camera_config.exists():
            print(f"Warning: Camera config not found at {camera_config}")
        self.detector = SquareDetector(str(camera_config))

    def _init_voice(self):
        voice_config = self.config_dir / "voice2text.yaml"
        try:
            self.voice = Voice2Text(str(voice_config))
        except Exception as e:
            print(f"Voice module init failed: {e}")
            self.voice = None
            self.ai_status_message = "Voice Init Failed"

    def _init_agents(self):
        if not self.global_config:
            print("Error: Global config missing. AI agents disabled.")
            self.vision_agent = None
            self.solution_agent = None
            self.image_agent = None
            return

        self.vision_agent = VisionAgent(self.global_config)
        self.solution_agent = SolutionAgent(self.global_config)
        self.image_agent = ImageGenAgent(self.global_config)

    def cleanup_temp(self):
        """Clean up the temporary directory on exit."""
        if self.temp_dir.exists():
            print(f"Cleaning up temp directory: {self.temp_dir}")
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True) # Recreate empty dir
            except Exception as e:
                print(f"Error cleaning temp dir: {e}")

    def run_ai_pipeline(self, image_path):
        """Runs the AI pipeline in a separate thread."""
        self.is_processing_ai = True
        self.ai_status_message = "Analyzing Image..."
        
        try:
            print("\n--- Starting AI Pipeline ---")
            
            # Step 1: Vision
            vision_result = self.vision_agent.analyze(str(image_path))
            if not vision_result:
                print("Vision analysis failed.")
                self.ai_status_message = "Vision Failed"
                return

            print(f"Vision Result: {vision_result.get('project_title', 'Unknown')}")
            self.ai_status_message = "Generating Solution..."
            
            # Step 2: Solution
            solution_result = self.solution_agent.generate(vision_result)
            if not solution_result:
                print("Solution generation failed.")
                self.ai_status_message = "Solution Failed"
                return

            print(f"Solution: {solution_result.get('project_name')}")
            self.ai_status_message = "Generating Preview..."
            
            # Step 3: Image Gen
            image_prompt = solution_result.get("image_prompt", "")
            preview_url = None
            if image_prompt:
                preview_url = self.image_agent.generate_image(image_prompt)
            
            if preview_url:
                print(f"Preview URL: {preview_url}")
                self.ai_status_message = "Pipeline Complete! Check Console."
            else:
                self.ai_status_message = "Pipeline Complete (No Image)."

            # Output JSON result
            final_output = {
                "vision": vision_result,
                "solution": solution_result,
                "preview_url": preview_url,
                "timestamp": datetime.now().isoformat()
            }
            print("\n=== Final Result ===")
            print(json.dumps(final_output, indent=2, ensure_ascii=False))
            print("====================\n")

        except Exception as e:
            print(f"AI Pipeline Error: {e}")
            self.ai_status_message = "Error in Pipeline"
        finally:
            self.is_processing_ai = False

    def handle_snapshot(self, frame):
        """Handles the 'a' key press for snapshot."""
        if self.is_processing_ai:
            print("AI is busy, please wait.")
            return

        print("Snapshot triggered!")
        
        # 1. Apply perspective transform
        # Note: detect.py's run() loop calls detect_white_square... then apply_perspective_transform.
        # We need to make sure detector.corners is populated. 
        # In our main loop we call detect_white_square_with_black_border which updates self.detector.corners.
        warped_frame = self.detector.apply_perspective_transform(frame)
        
        # 2. Save File
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"
        
        # Save to logs (permanent)
        log_path = self.logs_dir / filename
        cv2.imwrite(str(log_path), warped_frame)
        print(f"Saved to logs: {log_path}")
        
        # Save to temp (for processing)
        temp_path = self.temp_dir / filename
        cv2.imwrite(str(temp_path), warped_frame)
        
        # 3. Trigger AI Pipeline
        thread = threading.Thread(target=self.run_ai_pipeline, args=(temp_path,))
        thread.daemon = True
        thread.start()

    def handle_voice_logic(self):
        """
        Manages the 'hold b to record' logic.
        Should be called every frame.
        """
        if not self.voice:
            return

        current_time = time.time()
        
        # Check timeout
        if self.is_recording:
            if current_time - self.last_b_press_time > self.voice_timeout:
                # Timeout reached, stop recording
                self.voice.stop_recording()
                self.is_recording = False
                print("Voice recording stopped (key release detected).")
                
                # Transcribe
                print("Transcribing voice...")
                text = self.voice.transcribe_audio()
                if text:
                    print(f"\n[Voice Command]: {text}\n")
                    self.ai_status_message = f"Voice: {text[:20]}..."
                else:
                    print("Voice transcription failed or empty.")
                    self.ai_status_message = "Voice: No text"

    def run(self):
        """Main application loop."""
        self.cap = cv2.VideoCapture(self.camera_id)
        
        # Set camera parameters
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        if not self.cap.isOpened():
            print("Error: Could not open camera.")
            return

        print("\n=== SparkBox System Ready ===")
        print("Controls:")
        print("  [A] - Take Snapshot & Analyze")
        print("  [B] - Hold to Record Voice")
        print("  [Q] - Quit")
        print("=============================\n")

        window_name = "SparkBox Main"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to grab frame.")
                    break

                # Detection (Updates internal state of detector)
                detected_frame, _ = self.detector.detect_white_square_with_black_border(frame)

                # Overlay Status
                status_color = (0, 255, 0) if not self.is_processing_ai else (0, 165, 255)
                cv2.putText(detected_frame, f"Status: {self.ai_status_message}", (20, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
                
                if self.is_recording:
                    cv2.circle(detected_frame, (50, 80), 15, (0, 0, 255), -1)
                    cv2.putText(detected_frame, "REC", (80, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                cv2.imshow(window_name, detected_frame)

                # Input Handling
                key = cv2.waitKey(10) & 0xFF
                
                # Debug print for keys (ignore no-press)
                if key != 255:
                    print(f"Key pressed: {key} ({chr(key) if 32 <= key <= 126 else '?'})")

                if key == ord('q'):
                    print("Quitting...")
                    break
                
                elif key == ord('a'):
                    self.handle_snapshot(frame)
                
                elif key == ord('b'):
                    self.last_b_press_time = time.time()
                    if not self.is_recording:
                        if self.voice:
                            self.voice.start_recording()
                            self.is_recording = True
                        else:
                            print("Voice module not available.")

                # Voice Logic Check (every loop)
                self.handle_voice_logic()

        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            if self.cap:
                self.cap.release()
            if self.voice:
                self.voice.close()
            cv2.destroyAllWindows()
            self.cleanup_temp()

if __name__ == "__main__":
    app = SparkBoxApp()
    app.run()
