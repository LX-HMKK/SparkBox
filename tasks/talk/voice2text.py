import os
import yaml
import json
import cv2
import pyaudio
import wave
import dashscope
from http import HTTPStatus
from dashscope.audio.asr import Recognition
import numpy as np
import threading
import sys

class Voice2Text:
    def __init__(self, config_path=None):
        """
        初始化：加载配置、设置API Key、准备录音环境。
        """
        # Calculate base_dir first as it's needed for both config and asset paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if config_path is None:
            config_path = os.path.join(base_dir, 'config', 'voice2text.yaml')
        
        self.config = self._load_config(config_path)
        
        api_key = self.config.get('dashscope_api_key')
        if not api_key:
            raise ValueError("dashscope_api_key not found in config")
        dashscope.api_key = api_key
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000

        # Save recorder file to asset directory
        recorder_filename = self.config.get('recorder_file', 'recorder.wav')
        asset_dir = os.path.join(base_dir, 'asset')
        os.makedirs(asset_dir, exist_ok=True)
        self.recorder_file = os.path.join(asset_dir, recorder_filename)
        
        # Recording state
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.p = pyaudio.PyAudio()
        self._record_thread = None
        self._stop_event = threading.Event()
        self._frames_lock = threading.Lock()

    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def start_recording(self):
        """开始录音，打开音频流。"""
        # 每次开始录音前，先删除旧的录音文件
        if os.path.exists(self.recorder_file):
            try:
                os.remove(self.recorder_file)
                print(f"Removed old recording file: {self.recorder_file}")
            except OSError as e:
                print(f"Error removing file {self.recorder_file}: {e}")

        if self.is_recording:
            print("Already recording.")
            return
        print("Recording started...")
        self.is_recording = True
        with self._frames_lock:
            self.frames = []
        self._stop_event.clear()
        
        try:
            # 尝试打开音频流，添加错误处理
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
        except Exception as e:
            print(f"Warning: Failed to open stream with rate {self.rate}: {e}")
            print("Trying with device default rate 44100...")
            try:
                # 尝试使用44100 Hz（RDK默认采样率）
                self.rate = 44100
                self.stream = self.p.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk
                )
                print(f"Successfully opened stream with rate {self.rate}")
            except Exception as e2:
                print(f"Error: Cannot open audio stream: {e2}")
                self.is_recording = False
                raise

        # 启动后台线程，避免主循环阻塞导致丢音
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()

    def stop_recording(self):
        """停止录音，关闭音频流并保存文件。"""
        if not self.is_recording:
            return False
        
        print("Recording stopped.")
        self.is_recording = False
        self._stop_event.set()
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=2.0)
        self._record_thread = None
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error closing audio stream: {e}")
            finally:
                self.stream = None

        with self._frames_lock:
            has_frames = bool(self.frames)
            frames_copy = list(self.frames)

        if not has_frames:
            print("No audio recorded.")
            return False

        # Save the recorded data as a WAV file
        wf = wave.open(self.recorder_file, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames_copy))
        wf.close()
        print(f"Audio saved to {self.recorder_file}")
        return True

    def read_audio_chunk(self):
        """从音频流中读取一个数据块。"""
        # 若后台线程已接管录音，这里无需重复读取
        if self._record_thread and self._record_thread.is_alive():
            return
        if self.is_recording and self.stream:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                with self._frames_lock:
                    self.frames.append(data)
            except Exception as e:
                print(f"Audio read error: {e}")
                # 防止异常导致主线程崩溃
                self.is_recording = False

    def _record_loop(self):
        """后台录音循环，确保持续读取音频，避免主线程阻塞丢帧。"""
        while self.is_recording and not self._stop_event.is_set():
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                with self._frames_lock:
                    self.frames.append(data)
            except Exception as e:
                print(f"Audio read error: {e}")
                self.is_recording = False
                break

    def transcribe_audio(self):
        """转写已保存的音频文件。"""
        if not os.path.exists(self.recorder_file):
            print(f"Audio file not found: {self.recorder_file}")
            return None

        print("Transcribing...")
        print(f"Using sample rate: {self.rate} Hz")
        try:
            recognition = Recognition(model='paraformer-realtime-v2',
                                      format='wav',
                                      sample_rate=self.rate,  # 使用实际采样率
                                      callback=None)
            response = recognition.call(file=self.recorder_file)
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

        if response.status_code == HTTPStatus.OK:
            if response.output and 'sentence' in response.output:
                text = "".join([s['text'] for s in response.output['sentence']])
                return text
            else:
                return json.dumps(response.output, ensure_ascii=False)
        else:
            print(f"Transcription failed: {response.code} - {response.message}")
            return None
            
    def close(self):
        """关闭并释放 PyAudio 资源。"""
        if self.stream:
            self.stream.close()
        self.p.terminate()
        print("PyAudio resources released.")


if __name__ == "__main__":
    # Check for CLI mode argument
    if len(sys.argv) > 1 and sys.argv[1] in ['--cli', '--console', '-c']:
        import time
        import select
        import tty
        import termios
        
        v2t = Voice2Text()
        print("=== Console Voice Recorder Mode ===")
        print("Controls: [r] Record  [s] Stop  [q] Quit")
        
        def is_data():
            return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            
            while True:
                if is_data():
                    key = sys.stdin.read(1).lower()
                    
                    if key == 'q':
                        if v2t.is_recording:
                            v2t.stop_recording()
                        print("\nQuitting...")
                        break
                    
                    elif key == 'r':
                        if not v2t.is_recording:
                            v2t.start_recording()
                            
                    elif key == 's':
                        if v2t.is_recording:
                            if v2t.stop_recording():
                                print("Transcribing...")
                                text = v2t.transcribe_audio()
                                if text:
                                    print("-" * 30)
                                    print("Recognition Result:")
                                    print(text)
                                    print("-" * 30)
                                print("Ready. [r] Record [q] Quit")
                
                time.sleep(0.05)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            if v2t.is_recording:
                v2t.stop_recording()
            v2t.close()
            print("Exited.")

    else:
        # Original GUI Mode
        v2t = Voice2Text()
        
        window_name = "Voice Recorder Control"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 400, 100)
        
        img_ready = np.zeros((100, 400, 3), dtype=np.uint8)
        cv2.putText(img_ready, "Press 'r' to START", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        img_rec = np.zeros((100, 400, 3), dtype=np.uint8)
        cv2.putText(img_rec, "Recording... 's' to STOP", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        print("Control Window Open.")
        print("Press 'r' to START recording.")
        print("Press 's' to STOP recording.")
        print("Press 'q' to QUIT.")
        
        # cv2.imshow(window_name, img_ready)
        
        audio_saved = False
        
        while True:
            key = cv2.waitKey(10) & 0xFF
            
            if v2t.is_recording:
                v2t.read_audio_chunk()
                cv2.imshow(window_name, img_rec)
            else:
                cv2.imshow(window_name, img_ready)

            if key == ord('r'):
                v2t.start_recording()
            elif key == ord('s'):
                if v2t.is_recording:
                    audio_saved = v2t.stop_recording()
                    # GUI模式下原逻辑是录一次就退出循环，这里保持原样，或者你可以去掉break使其循环使用
                    text = v2t.transcribe_audio()
                    if text is not None:
                        print("\nRecognition Result:")
                        print(text)
                    # break # Commented out break to allow multiple recordings in GUI mode as well, simpler experience
                    audio_saved = False 
            elif key == ord('q'):
                v2t.stop_recording() # Ensure stream is closed if recording
                break
                
        cv2.destroyAllWindows()
        v2t.close()
