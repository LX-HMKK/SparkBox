"""
SparkBox Windows版本 - 适用于上位机调试
移除了GPIO依赖，仅使用键盘控制
集成 Flask Web 服务器实现动态前端显示
"""
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
from flask import Flask, render_template, Response, jsonify, request
from queue import Queue
import webbrowser

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
        self.is_b_key_pressed = False
        
        # AI pipeline results
        self.last_vision_result = None
        self.last_solution_result = None
        self.last_complete_result = None
        
        # Web/video state
        self.web_mode = True
        self.latest_frame = None  # processed frame with overlays
        self.latest_raw_frame = None  # original frame
        self.frame_lock = threading.Lock()
        
        # Web Server Event Queue for SSE
        self.event_queue = Queue()
        self.latest_status = {
            "state": "ready",
            "message": "System Ready",
            "data": None
        }
        
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
        "Clean up the temporary directory on exit."
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
        self._push_event("processing", "Analyzing Image...")
        
        try:
            print("\n--- Starting AI Pipeline ---")
            
            # Step 1: Vision
            self._push_event("processing", "Vision Analysis...")
            vision_result = self.vision_agent.analyze(str(image_path))
            if not vision_result:
                print("Vision analysis failed.")
                self.ai_status_message = "Vision Failed"
                return

            # Save vision result
            self.last_vision_result = vision_result

            print(f"Vision Result: {vision_result.get('project_title', 'Unknown')}")
            self.ai_status_message = "Generating Solution..."
            self._push_event("processing", "Generating Solution...", {"vision": vision_result})
            
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
            self._push_event("processing", "Generating Preview Image...")
            
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
            
            # Save complete result
            self.last_complete_result = final_output
            
            print("\n=== Final Result ===")
            print(json.dumps(final_output, indent=2, ensure_ascii=False))
            print("====================\n")
            
            # Push complete event to web clients
            self._push_event("complete", "Analysis Complete!", final_output)

        except Exception as e:
            print(f"AI Pipeline Error: {e}")
            self.ai_status_message = "Error in Pipeline"
            self._push_event("error", str(e))
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
            self._push_event("error", "Voice transcription failed")

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

    def _push_event(self, state, message, data=None):
        """Push event to web clients via SSE"""
        event_data = {
            "state": state,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.latest_status = event_data
        self.event_queue.put(event_data)
    
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

    def run(self):
        "Main application loop."
        self.cap = cv2.VideoCapture(self.camera_id)
        
        # Set camera parameters
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        if not self.cap.isOpened():
            print("Error: Could not open camera.")
            return

        print("\n=== SparkBox System Ready (Web Mode) ===")
        print("Use the web UI to trigger actions.")
        print("===============================================\n")

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to grab frame.")
                    break

                # Store raw frame
                with self.frame_lock:
                    self.latest_raw_frame = frame

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

                # Publish latest processed frame for web streaming
                with self.frame_lock:
                    self.latest_frame = detected_frame

                # Small sleep to reduce CPU usage
                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            if self.cap:
                self.cap.release()
            if self.voice:
                self.voice.close()
            print("Application cleaned up.")

# ==========================================
# Flask Web Server
# ==========================================
web_app = Flask(__name__, 
                template_folder=str(TASKS_DIR / "ui_output" / "templates"),
                static_folder=str(TASKS_DIR / "ui_output" / "static"))

# Global reference to SparkBox instance
sparkbox_instance = None

@web_app.route('/')
def index():
    return render_template('sparkbox.html')

@web_app.route('/old')
def old_index():
    return render_template('index.html')

@web_app.route('/api/status')
def api_status():
    """Return current status as JSON"""
    if sparkbox_instance:
        return jsonify(sparkbox_instance.latest_status)
    return jsonify({"state": "offline", "message": "System offline"})

@web_app.route('/api/result')
def api_result():
    """Return latest complete result"""
    if sparkbox_instance and sparkbox_instance.last_complete_result:
        return jsonify(sparkbox_instance.last_complete_result)
    return jsonify({"error": "No results available"})

@web_app.route('/api/voice/start', methods=['POST'])
def api_voice_start():
    """Start voice recording"""
    if not sparkbox_instance:
        return jsonify({"error": "System offline"}), 503
    if not sparkbox_instance.voice:
        return jsonify({"error": "Voice module unavailable"}), 400
    if sparkbox_instance.is_recording:
        return jsonify({"status": "already_recording"})
    try:
        sparkbox_instance.voice.start_recording()
        sparkbox_instance.is_recording = True
        sparkbox_instance._push_event("processing", "Voice recording started")
        return jsonify({"status": "recording_started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@web_app.route('/api/voice/stop', methods=['POST'])
def api_voice_stop():
    """Stop voice recording and transcribe"""
    if not sparkbox_instance:
        return jsonify({"error": "System offline"}), 503
    if not sparkbox_instance.voice:
        return jsonify({"error": "Voice module unavailable"}), 400
    if not sparkbox_instance.is_recording:
        return jsonify({"status": "not_recording"})
    try:
        sparkbox_instance.voice.stop_recording()
        sparkbox_instance.is_recording = False
        # Transcribe + chat in background
        thread = threading.Thread(target=sparkbox_instance.transcribe_and_chat, daemon=True)
        thread.start()
        return jsonify({"status": "recording_stopped"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@web_app.route('/api/quit', methods=['POST'])
def api_quit():
    """Gracefully stop main loop"""
    if not sparkbox_instance:
        return jsonify({"error": "System offline"}), 503
    sparkbox_instance.running = False
    return jsonify({"status": "stopping"})

@web_app.route('/api/snapshot', methods=['POST'])
def api_snapshot():
    """Trigger snapshot using the latest raw frame"""
    if not sparkbox_instance:
        return jsonify({"error": "System offline"}), 503
    with sparkbox_instance.frame_lock:
        frame = sparkbox_instance.latest_raw_frame
    if frame is None:
        return jsonify({"error": "No camera frame available"}), 400
    # Run snapshot handling in background
    threading.Thread(target=sparkbox_instance.handle_snapshot, args=(frame,), daemon=True).start()
    return jsonify({"status": "snapshot_triggered"})

@web_app.route('/video_feed')
def video_feed():
    """MJPEG streaming of latest processed frames"""
    def generate():
        boundary = "frame"
        while True:
            frame_copy = None
            if sparkbox_instance:
                with sparkbox_instance.frame_lock:
                    if sparkbox_instance.latest_frame is not None:
                        frame_copy = sparkbox_instance.latest_frame.copy()
            if frame_copy is not None:
                ok, buffer = cv2.imencode('.jpg', frame_copy)
                if ok:
                    jpg_bytes = buffer.tobytes()
                    yield (b"--" + boundary.encode() + b"\r\n"
                           b"Content-Type: image/jpeg\r\n"
                           b"Content-Length: " + str(len(jpg_bytes)).encode() + b"\r\n\r\n" + jpg_bytes + b"\r\n")
            else:
                # If no frame yet, wait a bit
                time.sleep(0.05)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@web_app.route('/stream')
def stream():
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        while True:
            if sparkbox_instance:
                try:
                    # Wait for new events with timeout
                    event = sparkbox_instance.event_queue.get(timeout=30)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except:
                    # Send keepalive
                    yield f"data: {{\"type\": \"keepalive\"}}\n\n"
            else:
                time.sleep(1)
    
    return Response(event_stream(), mimetype="text/event-stream")

def run_flask_server():
    """Run Flask server in a separate thread"""
    web_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    # Create SparkBox instance
    app = SparkBoxApp()
    sparkbox_instance = app
    
    # Start Flask server in background
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    print("\n" + "="*50)
    print("Web Interface: http://localhost:5000")
    print("="*50 + "\n")
    # Auto-open browser
    try:
        webbrowser.open_new_tab("http://localhost:5000")
    except Exception:
        pass
    
    # Run main camera loop
    app.run()
