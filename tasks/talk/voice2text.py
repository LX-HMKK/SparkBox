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

class Voice2Text:
    def __init__(self, config_path=None):
        """
        初始化：加载配置、设置API Key、准备录音环境。
        """
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        self.recorder_file = self.config.get('recorder_file', 'recorder.wav')
        
        # Recording state
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.p = pyaudio.PyAudio()

    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def start_recording(self):
        """开始录音，打开音频流。"""
        if self.is_recording:
            print("Already recording.")
            return
        print("Recording started...")
        self.is_recording = True
        self.frames = []
        self.stream = self.p.open(format=self.format,
                                  channels=self.channels,
                                  rate=self.rate,
                                  input=True,
                                  frames_per_buffer=self.chunk)

    def stop_recording(self):
        """停止录音，关闭音频流并保存文件。"""
        if not self.is_recording:
            return False
        
        print("Recording stopped.")
        self.is_recording = False
        self.stream.stop_stream()
        self.stream.close()
        self.stream = None

        if not self.frames:
            print("No audio recorded.")
            return False

        # Save the recorded data as a WAV file
        wf = wave.open(self.recorder_file, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        print(f"Audio saved to {self.recorder_file}")
        return True

    def read_audio_chunk(self):
        """从音频流中读取一个数据块。"""
        if self.is_recording and self.stream:
            data = self.stream.read(self.chunk)
            self.frames.append(data)

    def transcribe_audio(self):
        """转写已保存的音频文件。"""
        if not os.path.exists(self.recorder_file):
            print(f"Audio file not found: {self.recorder_file}")
            return None

        print("Transcribing...")
        recognition = Recognition(model='paraformer-realtime-v2',
                                  format='wav',
                                  sample_rate=16000,
                                  callback=None)
        
        response = recognition.call(file=self.recorder_file)

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
    
    cv2.imshow(window_name, img_ready)
    
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
                break
        elif key == ord('q'):
            v2t.stop_recording() # Ensure stream is closed if recording
            break
            
    cv2.destroyAllWindows()

    if audio_saved:
        text = v2t.transcribe_audio()
        if text is not None:
            print("\nRecognition Result:")
            print(text)
    
    v2t.close()
