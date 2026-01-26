"""
SparkBox Arm版本 - 适用于开发板部署
集成 GPIO 按键控制、摄像头采集和 Web 服务
"""
import sys
import time
import yaml
import shutil
import atexit
import threading
from pathlib import Path

# Try to import GPIO, if failed, maybe verify environment
try:
    import Hobot.GPIO as GPIO
except ImportError:
    print("Warning: Hobot.GPIO not found. GPIO buttons will not work.")
    GPIO = None

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_DIR = BASE_DIR / "tasks"

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
    from io_input import GPIOButton, load_gpio_config
except ImportError as e:
    print(f"Error importing modules: {e}")
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
        atexit.register(self.cleanup)
        
        # Load Configurations
        self.global_config = self._load_config(self.config_dir / "config.yaml")
        
        # Initialize Modules
        print("Initializing modules...")
        self._init_detector()
        self._init_voice()
        self._init_agents()
        self._init_managers()
        self._init_gpio()
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
        self.camera_manager = CameraManager(camera_id=0, width=1280, height=720)
        
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

    def _init_gpio(self):
        """初始化 GPIO 按键"""
        self.gpio_buttons = {}
        # 为了实现 Capture 键的长按逻辑
        self.capture_press_start_time = 0
        self.capture_was_pressed = False
        
        # 语音模式状态
        self.in_voice_mode = False
        self.video_release_required = False
        
        # 防抖冷却
        self.last_capture_time = 0
        self.capture_cooldown = 1.0 # 1秒冷却，防止连击
        
        # 防止 Reset 后误触 Snapshot
        self.last_reset_time = 0
        self.reset_refractory_period = 2.0 # Reset 后2秒内不接受拍照
        
        if GPIO is None:
            return

        io_config_path = self.config_dir / "io.yaml"
        print(f"Loading GPIO config from {io_config_path}")
        
        try:
            self.gpio_config = load_gpio_config(str(io_config_path))
            if not self.gpio_config:
                print("Warning: GPIO configuration not loaded.")
                return
            
            print("--- GPIO Button Configuration ---")
            for name, config in self.gpio_config.items():
                if isinstance(config, dict) and 'pin' in config:
                    pin = config['pin']
                    # mode = config.get('mode', 'single')
                    # 初始化 GPIOButton (假设开发板按键是低电平触发 active_low=True)
                    try:
                        self.gpio_buttons[name] = GPIOButton(pin, active_low=True, bouncetime=100)
                        print(f"  Initialized {name} on Pin {pin}")
                    except Exception as e:
                        print(f"  Failed to init {name}: {e}")
            print("--------------------------------\n")
            
        except Exception as e:
            print(f"GPIO button initialization failed: {e}")

    def cleanup(self):
        "Clean up resources on exit."
        # Clean up temp directory
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        
        # Clean up GPIO
        if GPIO:
            try:
                GPIO.cleanup()
                print("GPIO resources cleaned up.")
            except: pass
            
        # Clean up managers
        if hasattr(self, 'camera_manager'):
            self.camera_manager.cleanup()
        if self.voice:
            self.voice.close()

    def handle_gpio(self):
        """处理 GPIO 输入循环 - 根据当前状态动态调整按键行为"""
        if not self.gpio_buttons:
            return

        # 获取当前应用的状态 (idle, processing, done, error 等)
        # 我们假设 ai_manager 中有一个状态可以查询，或者我们通过 self.ai_manager.is_busy() 简单判断
        # 更精细的控制可以增加一个 self.app_state 变量
        current_ai_status = self.ai_manager.get_status() # {"status_message": "...", "is_processing": True/False, "step": "..."}
        is_processing = current_ai_status.get("is_processing", False)
        
        # -------------------
        # 1. Capture 键 (Pin 16)
        # -------------------
        # 逻辑修改：
        # - 如果系统空闲 (Idle) -> Capture = 拍照
        # - 如果系统已有结果 (Result) -> Capture = 重置 (下一题)
        # - 不再依赖长短按区分
        if 'capture' in self.gpio_buttons:
            btn = self.gpio_buttons['capture']
            
            # 使用 get_press() 获取一次性的按下事件，不关心时长
            if btn.get_press():
                now = time.time()
                # 防抖冷却检查
                if now - self.last_capture_time < self.capture_cooldown:
                    print(f"  -> Capture Ignored (Cooldown: {now - self.last_capture_time:.2f}s)")
                else:
                    self.last_capture_time = now
                    print("[GPIO] Capture Button Triggered")
                    
                    # 如果正在处理中，忽略按键
                    if is_processing:
                         print("  -> System Busy, Ignored.")
                    
                    # 如果当前没有结果（空闲状态），则执行【拍照】
                    elif not self.ai_manager.has_result: 
                        # 检查是否刚重置过 (防止 Reset 按键的释放动作或弹跳误触发拍照)
                        if now - self.last_reset_time < self.reset_refractory_period:
                            print(f"  -> Reset refractory period active ({now - self.last_reset_time:.2f}s < {self.reset_refractory_period}s). Snapshot ignored.")
                        else:
                            print("  -> Context: Idle -> Action: Snapshot")
                            self.trigger_snapshot()
                        
                    # 如果当前已有结果，则执行【重置/下一题】
                    else:
                        print("  -> Context: Result Shown -> Action: Reset")
                        self.handle_reset()

        # -------------------
        # 2. Video 键 (Pin 18)
        # -------------------
        # 逻辑：在结果页按一下进入语音模式，在语音模式按住说话
        if 'video' in self.gpio_buttons:
            btn = self.gpio_buttons['video']
            
            # Logic: Switch Mode vs Recording
            if self.ai_manager.has_result and not self.in_voice_mode:
                # 尚未进入语音模式 -> 按键触发模式切换
                if btn.get_press():
                    print("[GPIO] Video Button -> Enter Voice Mode")
                    self.in_voice_mode = True
                    self.video_release_required = True
                    self.web_manager.push_event("control", "Enter Voice", {"action": "enter_voice"})
            
            elif self.in_voice_mode:
                # 已在语音模式 -> PTT 逻辑
                is_pressed = btn.is_pressed()
                
                # 如果刚切换模式，需等待按键释放
                if self.video_release_required:
                    if not is_pressed:
                        self.video_release_required = False
                else:
                    # 正常的按住录音逻辑
                    if is_pressed:
                        # 键被按下
                        if self.voice and not self.voice.is_recording:
                            print("[GPIO] Video Pressed -> Start Recording")
                            self.web_manager.push_event("voice_recording", "正在录音...")
                            self.voice.start_recording()
                    else:
                        # 键未按下
                        if self.voice and self.voice.is_recording:
                            print("[GPIO] Video Released -> Stop Recording")
                            self.voice.stop_recording()
                            # 启动异步线程处理录音结果
                            threading.Thread(target=self.process_voice_after_record).start()

        # -------------------
        # 3. PGUP (Pin 22) -> 前翻
        # -------------------
        if 'PGUP' in self.gpio_buttons:
            if self.gpio_buttons['PGUP'].get_press():
                print("[GPIO] PGUP -> Prev Slide/Page")
                self.web_manager.push_event("control", "Previous", {"action": "prev"})

        # -------------------
        # 4. PGDN (Pin 36) -> 后翻
        # -------------------
        if 'PGDN' in self.gpio_buttons:
            if self.gpio_buttons['PGDN'].get_press():
                print("[GPIO] PGDN -> Next Slide/Page")
                self.web_manager.push_event("control", "Next", {"action": "next"})

    def trigger_snapshot(self):
        """触发拍照流程"""
        if self.ai_manager.is_busy():
            print("AI Manager is busy, skipping snapshot.")
            self.web_manager.push_event("error", "系统忙，请稍后")
            return

        frame = self.camera_manager.get_latest_raw_frame()
        if frame is None:
            print("Error: No frame to capture.")
            return

        self.handle_snapshot(frame)

    def handle_snapshot(self, frame):
        """处理快照逻辑"""
        print("\n📸 GPIO Snapshot Triggered")
        self.web_manager.push_event("processing", "正在分析图像...")
        self.in_voice_mode = False  # Reset voice mode
        
        try:
            log_path, temp_path = self.camera_manager.save_snapshot(
                frame, self.detector, self.logs_dir, self.temp_dir
            )
            print(f"Snapshot saved to {temp_path}")
            self.ai_manager.run_ai_pipeline_async(temp_path)
            
        except Exception as e:
            print(f"Snapshot Failed: {e}")
            self.web_manager.push_event("error", f"快照失败: {str(e)}")

    def handle_reset(self):
        """触发系统重置"""
        print("🔄 System Resetting...")
        self.ai_manager.reset_results()
        self.last_reset_time = time.time()  # 记录重置时间
        self.in_voice_mode = False  # Reset voice mode
        self.video_release_required = False
        self.web_manager.push_event("control", "Reset", {"action": "reset"})

    def process_voice_after_record(self):
        """处理录音结束后的逻辑"""
        try:
            print("Transcribing audio...")
            text = self.voice.transcribe_audio()
            if text:
                print(f"Voice recognized: {text}")
                self.web_manager.push_event("voice_user", text)
                self.ai_manager.run_chat_ai_async(text)
            else:
                print("Voice transcription empty.")
                self.web_manager.push_event("voice_error", "未识别到语音")
        except Exception as e:
            print(f"Voice process error: {e}")
            self.web_manager.push_event("voice_error", "语音处理出错")

    def run(self):
        "Main application loop"
        
        # 初始化摄像头
        try:
            self.camera_manager.initialize_camera()
        except RuntimeError as e:
            print(f"Camera initialization failed: {e}")
            return
        
        print("\n=== SparkBox Arm System Ready ===")
        print("Services: GPIO, Camera, AI, WebServer")
        print("Controls:")
        print("  Capture (Pin 16): Short=Photo, Long=Reset")
        print("  Video   (Pin 18): Hold=Record Voice")
        print("  PGUP    (Pin 22): Prev Slide")
        print("  PGDN    (Pin 36): Next Slide")
        print("=======================================\n")
        
        # Start Flask server (Auto open browser in Kiosk mode)
        self.web_manager.start_server_async(debug=False, auto_open_browser=True)
        
        try:
            while self.running:
                # 1. Camera Frame
                ret, frame = self.camera_manager.get_frame()
                if not ret:
                    print("Failed to grab frame.")
                    break
                
                # 2. Detection (Detect square)
                detected_frame, _ = self.detector.detect_white_square_with_black_border(frame)
                
                # 3. Update Status for Managers
                ai_status = self.ai_manager.get_status()
                self.camera_manager.update_status(
                    ai_status["status_message"],
                    ai_status["is_processing"],
                    self.voice.is_recording if self.voice else False
                )
                
                # 4. Handle Voice Stream Buffering if detecting
                if self.voice and self.voice.is_recording:
                    self.voice.read_audio_chunk()
                
                # 5. Process Frame for Web View
                detected_frame = self.camera_manager.add_status_overlay(detected_frame)
                self.camera_manager.update_processed_frame(detected_frame)
                
                # 6. GPIO Event Handling
                self.handle_gpio()
                
                # Loop Delay
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            self.cleanup()

if __name__ == "__main__":
    app = SparkBoxApp()
    app.run()
