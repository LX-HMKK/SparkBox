"""
Web管理器 - 负责Flask Web服务器和API管理
"""
import json
import time
import threading
import webbrowser
from datetime import datetime
from queue import Queue
from flask import Flask, render_template, Response, jsonify, request
import cv2


class WebManager:
    def __init__(self, templates_folder, static_folder, host='0.0.0.0', port=5000):
        """
        初始化Web管理器
        
        Args:
            templates_folder: 模板文件夹路径
            static_folder: 静态文件夹路径
            host: 服务器主机
            port: 服务器端口
        """
        self.host = host
        self.port = port
        
        # Create Flask app
        self.app = Flask(__name__, 
                        template_folder=templates_folder,
                        static_folder=static_folder)
        
        # Event system for SSE
        self.event_queue = Queue()
        self.latest_status = {
            "state": "ready",
            "message": "System Ready",
            "data": None
        }
        
        # External references (to be set by main app)
        self.camera_manager = None
        self.ai_manager = None
        self.voice_handler = None
        self.app_instance = None
        
        # Setup routes
        self._setup_routes()
    
    def set_managers(self, camera_manager, ai_manager, voice_handler=None, app_instance=None):
        """设置外部管理器引用"""
        self.camera_manager = camera_manager
        self.ai_manager = ai_manager
        self.voice_handler = voice_handler
        self.app_instance = app_instance
    
    def push_event(self, state, message, data=None):
        """推送事件到Web客户端"""
        event_data = {
            "state": state,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        print(f"[WebManager] 推送事件: state={state}, message={message[:50] if message else None}...")
        self.latest_status = event_data
        self.event_queue.put(event_data)
        print(f"[WebManager] 事件已放入队列，队列大小: {self.event_queue.qsize()}")
    
    def _setup_routes(self):
        """设置Flask路由"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/old')
        def old_index():
            return render_template('index.html')
        
        @self.app.route('/api/status')
        def api_status():
            """返回当前状态"""
            if self.ai_manager:
                status = self.ai_manager.get_status()
                return jsonify({
                    "state": "processing" if status["is_processing"] else "ready",
                    "message": status["status_message"],
                    "data": status
                })
            return jsonify({"state": "offline", "message": "System offline"})
        
        @self.app.route('/api/result')
        def api_result():
            """返回最新完整结果"""
            if self.ai_manager and self.ai_manager.last_complete_result:
                return jsonify(self.ai_manager.last_complete_result)
            return jsonify({"error": "No results available"})
        
        @self.app.route('/api/snapshot', methods=['POST'])
        def api_snapshot():
            """触发快照分析"""
            print("=" * 50)
            print("📸 拍照API请求收到！")
            print(f"  摄像头管理器: {self.camera_manager is not None}")
            print(f"  AI管理器: {self.ai_manager is not None}")
            print("=" * 50)
            
            if not self.camera_manager or not self.ai_manager:
                print("❌ 系统离线")
                return jsonify({"error": "System offline"}), 503
            
            frame = self.camera_manager.get_latest_raw_frame()
            if frame is None:
                return jsonify({"error": "No camera frame available"}), 400
            
            # Trigger snapshot in background
            threading.Thread(
                target=self._handle_snapshot_api, 
                args=(frame,), 
                daemon=True
            ).start()
            
            return jsonify({"status": "snapshot_triggered"})
        
        @self.app.route('/api/voice/start', methods=['POST'])
        def api_voice_start():
            """开始语音录制"""
            if not self.voice_handler:
                return jsonify({"error": "Voice module unavailable"}), 400
            if self.voice_handler.is_recording:
                return jsonify({"status": "already_recording"})
            
            try:
                self.voice_handler.start_recording()
                self.camera_manager.update_status("Recording...", is_recording=True)
                # 使用专门的语音状态，避免与拍照processing冲突
                self.push_event("voice_recording", "开始录音...")
                return jsonify({"status": "recording_started"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/voice/stop', methods=['POST'])
        def api_voice_stop():
            """停止语音录制并转录"""
            if not self.voice_handler:
                return jsonify({"error": "Voice module unavailable"}), 400
            if not self.voice_handler.is_recording:
                return jsonify({"status": "not_recording"})
            
            try:
                self.voice_handler.stop_recording()
                self.camera_manager.update_status("Processing voice...", is_recording=False)
                # Transcribe + chat in background
                self.ai_manager.transcribe_and_chat_async()
                return jsonify({"status": "recording_stopped"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/quit', methods=['POST'])
        def api_quit():
            """优雅停止主循环"""
            if not self.app_instance:
                return jsonify({"error": "System offline"}), 503
            self.app_instance.running = False
            return jsonify({"status": "stopping"})
        
        @self.app.route('/video_feed')
        def video_feed():
            """MJPEG视频流"""
            def generate():
                boundary = "frame"
                while True:
                    frame_copy = None
                    if self.camera_manager:
                        frame_copy = self.camera_manager.get_latest_processed_frame()
                        if frame_copy is not None:
                            frame_copy = frame_copy.copy()
                    
                    if frame_copy is not None:
                        ok, buffer = cv2.imencode('.jpg', frame_copy)
                        if ok:
                            jpg_bytes = buffer.tobytes()
                            yield (b"--" + boundary.encode() + b"\r\n"
                                   b"Content-Type: image/jpeg\r\n"
                                   b"Content-Length: " + str(len(jpg_bytes)).encode() + b"\r\n\r\n" + jpg_bytes + b"\r\n")
                    else:
                        time.sleep(0.05)
            
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/stream')
        def stream():
            """服务器发送事件端点"""
            def event_stream():
                while True:
                    try:
                        # 首先获取一个事件（阻塞式等待）
                        event = self.event_queue.get(timeout=30)
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        
                        # 然后立即处理队列中所有剩余事件（非阻塞）
                        while not self.event_queue.empty():
                            try:
                                next_event = self.event_queue.get_nowait()
                                yield f"data: {json.dumps(next_event, ensure_ascii=False)}\n\n"
                            except:
                                break
                                
                    except:
                        # 超时后发送keepalive
                        yield f"data: {{\"type\": \"keepalive\"}}\n\n"
            
            return Response(event_stream(), mimetype="text/event-stream")
    
    def _handle_snapshot_api(self, frame):
        """处理API快照请求"""
        print("\n📸 处理快照API...")
        print(f"  AI忙碌状态: {self.ai_manager.is_busy()}")
        print(f"  应用实例存在: {self.app_instance is not None}")
        print(f"  handle_snapshot方法: {hasattr(self.app_instance, 'handle_snapshot') if self.app_instance else False}")
        
        if self.ai_manager.is_busy():
            print("⚠️ AI正在忙碌，请稍候")
            self.push_event("error", "AI正在处理中，请稍后再试")
            return
        
        print("✓ 快照触发成功，调用handle_snapshot")
        
        # This would need access to detector, logs_dir, temp_dir
        # For now, we'll delegate to the app instance
        if hasattr(self.app_instance, 'handle_snapshot'):
            self.app_instance.handle_snapshot(frame)
        else:
            print("❌ 应用实例没有handle_snapshot方法")
            self.push_event("error", "系统配置错误")
    
    def start_server(self, debug=False, auto_open_browser=True):
        """启动Flask服务器"""
        if auto_open_browser:
            # Auto-open browser
            def open_browser():
                time.sleep(1)  # Wait for server to start
                try:
                    webbrowser.open_new_tab(f"http://localhost:{self.port}")
                except Exception:
                    pass
            
            threading.Thread(target=open_browser, daemon=True).start()
        
        print("\n" + "="*50)
        print(f"Web Interface: http://localhost:{self.port}")
        print("="*50 + "\n")
        
        # Start Flask server
        self.app.run(
            host=self.host, 
            port=self.port, 
            debug=debug, 
            use_reloader=False, 
            threaded=True
        )
    
    def start_server_async(self, debug=False, auto_open_browser=True):
        """异步启动Flask服务器"""
        thread = threading.Thread(
            target=self.start_server, 
            args=(debug, auto_open_browser),
            daemon=True
        )
        thread.start()
        return thread