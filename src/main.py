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
    from io_input import GPIOButton, load_gpio_config
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure your project structure is correct.")
    sys.exit(1)

class SparkBoxApp:
    def __init__(self):
        self.running = True
        self.camera_id = 0  # Default camera
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
        self.is_b_key_pressed = False
        
        # AI pipeline results
        self.last_vision_result = None
        self.last_solution_result = None
        
        
        # GPIO Buttons
        self.gpio_buttons = {}
        self.gpio_config = None
        
        # Load Configurations
        self.global_config = self._load_config(self.config_dir / "config.yaml")
        
        # Initialize GPIO buttons
        self._init_gpio_buttons()
        
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

    def _init_gpio_buttons(self):
        "Initialize GPIO buttons from io.yaml configuration."
        io_config_path = self.config_dir / "io.yaml"
        try:
            self.gpio_config = load_gpio_config(str(io_config_path))
            if not self.gpio_config:
                print("Warning: GPIO configuration not loaded, falling back to keyboard controls")
                return
            
            print("--- GPIO Button Configuration ---")
            for name, config in self.gpio_config.items():
                if isinstance(config, dict) and 'pin' in config:
                    pin = config.get('pin')
                    debounce = config.get('debounce', 200)
                    mode = config.get('mode', 'single')
                    
                    try:
                        self.gpio_buttons[name] = GPIOButton(input_pin=pin, bouncetime=debounce)
                        print(f"  - {name}: Pin {pin} ({mode} mode)")
                    except Exception as e:
                        print(f"  - {name}: Failed to initialize (Pin {pin}): {e}")
            print("--------------------------------\n")
            
        except Exception as e:
            print(f"GPIO button initialization failed: {e}")
            print("Falling back to keyboard controls")

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
        "Clean up the temporary directory and GPIO resources on exit."
        # Clean up GPIO buttons
        try:
            import Hobot.GPIO as GPIO
            GPIO.cleanup()
            print("GPIO resources cleaned up.")
        except:
            pass
            
        # Clean up temp directory
        if self.temp_dir.exists():
            print(f"Cleaning up temp directory: {self.temp_dir}")
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True) # Recreate empty dir
            except Exception as e:
                print(f"Error cleaning temp dir: {e}")

    def run_ai_pipeline(self, image_path):
        "Runs the AI pipeline in a separate thread."
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

            # Save vision result
            self.last_vision_result = vision_result

            print(f"Vision Result: {vision_result.get('project_title', 'Unknown')}")
            self.ai_status_message = "Generating Solution..."
            
            # Step 2: Solution
            solution_result = self.solution_agent.generate(vision_result)
            if not solution_result:
                print("Solution generation failed.")
                self.ai_status_message = "Solution Failed"
                return

            # Save solution result
            self.last_solution_result = solution_result

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

    def transcribe_and_chat(self):
        "Helper function to run transcription and chat AI in a thread."
        text = self.voice.transcribe_audio()
        if text:
            print(f"\n[Voice Command]: {text}\n")
            self.ai_status_message = f"Voice: {text[:20]}..."
            self.run_chat_ai(text)
        else:
            print("Voice transcription failed or empty.")
            self.ai_status_message = "Voice: No text"

    def run_chat_ai(self, text):
        """Handles the chat AI logic in a separate thread."""
        if self.is_processing_ai:
            print("AI is busy, please wait.")
            return

        if not self.last_vision_result:
            print("No vision result to chat about. Please analyze an image first.")
            self.ai_status_message = "Chat Failed: No Context"
            return

        self.is_processing_ai = True
        self.ai_status_message = "AI Thinking..."
        
        try:
            print("\n--- Running Chat AI with Context ---")
            # Use generate with user_message to leverage memory
            new_solution = self.solution_agent.generate(
                vision_data=self.last_vision_result, 
                user_message=text
            )
            
            if new_solution:
                # Update the last solution with the new one
                self.last_solution_result = new_solution
                print(f"\n[AI Response]: New solution generated based on your feedback.")
                # Optionally, you can print parts of the new solution
                print(json.dumps(new_solution, indent=2, ensure_ascii=False))
                self.ai_status_message = "AI Responded!"
            else:
                print("AI chat failed or returned no response.")
                self.ai_status_message = "AI Chat Failed"

        except Exception as e:
            print(f"Chat AI Error: {e}")
            self.ai_status_message = "Error in Chat"
        finally:
            self.is_processing_ai = False

    def handle_snapshot(self, frame):
        "Handles the 'a' key press for snapshot."
        if self.is_processing_ai:
            print("AI is busy, please wait.")
            return

        print("Snapshot triggered!")
        
        # 1. Apply perspective transform
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

    def handle_gpio_buttons(self):
        "Handle GPIO button events for snapshot and other controls."
        # Handle capture button (single mode)
        if 'capture' in self.gpio_buttons:
            if self.gpio_buttons['capture'].get_press():
                if not self.is_processing_ai:
                    print("GPIO Capture button pressed!")
                    # Get current frame for processing
                    ret, frame = self.cap.read()
                    if ret:
                        self.handle_snapshot(frame)
                else:
                    print("AI is busy, GPIO capture ignored.")
        
        # Handle voice recording with GPIO
        if 'video' in self.gpio_buttons:
            is_pressed = self.gpio_buttons['video'].is_pressed()
            if is_pressed and not self.is_recording:
                self.voice.start_recording()
                self.is_recording = True
                print("Voice recording started (GPIO button)")
            elif not is_pressed and self.is_recording:
                self.voice.stop_recording()
                self.is_recording = False
                print("Voice recording stopped (GPIO button released)")
                # Transcribe in a separate thread
                thread = threading.Thread(target=self.transcribe_and_chat)
                thread.daemon = True
                thread.start()

    def run(self):
        "Main application loop."
        self.cap = cv2.VideoCapture(self.camera_id)
        
        # Set camera parameters
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        if not self.cap.isOpened():
            print("Error: Could not open camera.")
            return

        print("\n=== SparkBox System Ready ===")
        print("Controls:")
        print("  [A] - Take Snapshot & Analyze (Keyboard)")
        print("  [GPIO Capture] - Take Snapshot & Analyze (Button)")
        print("  [B] - Hold to Record Voice (Keyboard)")
        print("  [GPIO Video] - Hold to Record Voice (Button)")
        print("  [Q] - Quit (Keyboard)")
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
                    # Read audio chunk while recording
                    if self.voice:
                        self.voice.read_audio_chunk()
                    
                    # Visual indicator for recording
                    cv2.circle(detected_frame, (50, 80), 15, (0, 0, 255), -1)
                    cv2.putText(detected_frame, "REC", (80, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                cv2.imshow(window_name, detected_frame)

                # Handle GPIO buttons first (higher priority)
                self.handle_gpio_buttons()
                
                # Handle keyboard input (fallback)
                key = cv2.waitKey(10) & 0xFF

                if key == ord('q'):
                    print("Quitting...")
                    break
                
                elif key == ord('a'):
                    self.handle_snapshot(frame)
                
                # --- New Keyboard Voice Logic ---
                is_b_down = (key == ord('b'))

                if is_b_down and not self.is_b_key_pressed:
                    if self.voice and not self.is_recording:
                        self.voice.start_recording()
                        self.is_recording = True
                        print("Voice recording started (keyboard)...")

                elif not is_b_down and self.is_b_key_pressed:
                    if self.voice and self.is_recording:
                        print("Voice recording stopped (keyboard). Transcribing...")
                        self.voice.stop_recording()
                        self.is_recording = False
                        
                        thread = threading.Thread(target=self.transcribe_and_chat)
                        thread.daemon = True
                        thread.start()

                self.is_b_key_pressed = is_b_down

        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            if self.cap:
                self.cap.release()
            if self.voice:
                self.voice.close()
            
            cv2.destroyAllWindows()
            print("Application cleaned up.")

if __name__ == "__main__":
    app = SparkBoxApp()
    app.run()
