"""
SparkBox Windows版本 - 适用于上位机调试
移除了GPIO依赖，仅使用键盘控制
集成 Flask Web 服务器实现动态前端显示
"""
import sys
import time
import yaml
import shutil
import atexit
from pathlib import Path

# --- Path Setup ---
# Calculate the project root directory (d:\StudyWorks\3.1\item1\SparkBox)
BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_DIR = BASE_DIR / "tasks"

# Add task directories to sys.path to allow imports
sys.path.append(str(TASKS_DIR / "img_input"))
sys.path.append(str(TASKS_DIR / "talk"))
sys.path.append(str(TASKS_DIR / "ui_output"))

# --- Imports from project modules ---
try:
    from detect import SquareDetector
    from voice2text import Voice2Text
    from vision_module import VisionAgent
    from mentor_module import SolutionAgent
    from image_module import ImageGenAgent
    from camera_manager import CameraManager
    from ai_manager import AIManager
    from web_manager import WebManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure your project structure is correct.")
    sys.exit(1)

class SparkBoxApp:
    def __init__(self):
        self.running = True
        
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
        
        # Load Configurations
        self.global_config = self._load_config(self.config_dir / "config.yaml")
        
        # Initialize Modules
        print("Initializing modules...")
        self._init_detector()
        self._init_voice()
        self._init_agents()
        self._init_managers()
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
    
    def _init_managers(self):
        """初始化各个管理器"""
        # 初始化摄像头管理器
        self.camera_manager = CameraManager(camera_id=1, width=1280, height=720)
        
        # 初始化AI管理器
        self.ai_manager = AIManager(
            self.global_config,
            self.vision_agent,
            self.solution_agent,
            self.image_agent,
            self.voice
        )
        
        # 初始化Web管理器
        templates_folder = str(TASKS_DIR / "ui_output" / "templates")
        static_folder = str(TASKS_DIR / "ui_output" / "static")
        self.web_manager = WebManager(templates_folder, static_folder)
        
        # 设置管理器间的引用关系
        self.web_manager.set_managers(
            self.camera_manager, 
            self.ai_manager, 
            self.voice, 
            self
        )
        
        # 设置AI事件回调
        self.ai_manager.set_event_callback(self.web_manager.push_event)

    def cleanup_temp(self):
        "Clean up the temporary directory on exit."
        if self.temp_dir.exists():
            print(f"Cleaning up temp directory: {self.temp_dir}")
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True) # Recreate empty dir
            except Exception as e:
                print(f"Error cleaning temp dir: {e}")
    
    def handle_snapshot(self, frame):
        """处理快照 - 简化版，委托给管理器"""
        if self.ai_manager.is_busy():
            print("AI is busy, please wait.")
            return
        
        print("Snapshot triggered!")
        
        # 使用摄像头管理器保存快照
        try:
            log_path, temp_path = self.camera_manager.save_snapshot(
                frame, self.detector, self.logs_dir, self.temp_dir
            )
            
            # 触发AI流程
            self.ai_manager.run_ai_pipeline_async(temp_path)
            
        except Exception as e:
            print(f"Snapshot error: {e}")
    


    def run(self):
        "Main application loop - 使用管理器重构版本"
        
        # 初始化摄像头
        try:
            self.camera_manager.initialize_camera()
        except RuntimeError as e:
            print(f"Camera initialization failed: {e}")
            return
        
        print("\n=== SparkBox System Ready (Web Mode) ===")
        print("Use the web UI to trigger actions.")
        print("===============================================\n")
        
        try:
            while self.running:
                ret, frame = self.camera_manager.get_frame()
                if not ret:
                    print("Failed to grab frame.")
                    break
                
                # Detection (Updates internal state of detector)
                detected_frame, _ = self.detector.detect_white_square_with_black_border(frame)
                
                # Update camera manager status from AI manager
                ai_status = self.ai_manager.get_status()
                self.camera_manager.update_status(
                    ai_status["status_message"],
                    ai_status["is_processing"],
                    self.voice.is_recording if self.voice else False
                )
                
                # Read audio chunk while recording
                if self.voice and self.voice.is_recording:
                    self.voice.read_audio_chunk()
                
                # Add status overlay
                detected_frame = self.camera_manager.add_status_overlay(detected_frame)
                
                # Update processed frame for web streaming
                self.camera_manager.update_processed_frame(detected_frame)
                
                # Small sleep to reduce CPU usage
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            self.camera_manager.cleanup()
            if self.voice:
                self.voice.close()
            print("Application cleaned up.")

# Flask Web Server code moved to WebManager

if __name__ == "__main__":
    # Create SparkBox instance
    app = SparkBoxApp()
    
    # Start Flask server in background
    app.web_manager.start_server_async(debug=False, auto_open_browser=True)
    
    # Run main camera loop
    app.run()
