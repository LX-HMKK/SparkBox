"""
AI管理器 - 负责AI流程管理、语音处理和AI pipeline协调
"""
import threading
import json
from datetime import datetime
from pathlib import Path


class AIManager:
    def __init__(self, global_config, vision_agent, solution_agent, image_agent, voice_handler=None):
        """
        初始化AI管理器
        
        Args:
            global_config: 全局配置
            vision_agent: 视觉分析代理
            solution_agent: 解决方案代理
            image_agent: 图像生成代理
            voice_handler: 语音处理器(可选)
        """
        self.global_config = global_config
        self.vision_agent = vision_agent
        self.solution_agent = solution_agent
        self.image_agent = image_agent
        self.voice_handler = voice_handler
        
        # AI状态
        self.is_processing = False
        self.status_message = "Ready"
        
        # AI pipeline 结果
        self.last_vision_result = None
        self.last_solution_result = None
        self.last_complete_result = None
        
        # 事件回调
        self.event_callback = None
    
    def set_event_callback(self, callback):
        """设置事件回调函数"""
        self.event_callback = callback
    
    def _push_event(self, state, message, data=None):
        """推送事件"""
        if self.event_callback:
            self.event_callback(state, message, data)
    
    def run_ai_pipeline(self, image_path):
        """
        运行AI流程
        
        Args:
            image_path: 图像路径
        """
        self.is_processing = True
        self.status_message = "Analyzing Image..."
        self._push_event("processing", "Analyzing Image...")
        
        try:
            print("\n--- Starting AI Pipeline ---")
            
            # 清除旧的对话记忆，开始新的分析
            self.solution_agent.clear_memory()
            
            # Step 1: Vision Analysis
            self._push_event("processing", "Vision Analysis...")
            vision_result = self.vision_agent.analyze(str(image_path))
            if not vision_result:
                print("Vision analysis failed.")
                self.status_message = "Vision Failed"
                return
            
            # Save vision result
            self.last_vision_result = vision_result
            
            print(f"Vision Result: {vision_result.get('project_title', 'Unknown')}")
            self.status_message = "Generating Solution..."
            self._push_event("processing", "Generating Solution...", {"vision": vision_result})
            
            # Step 2: Solution Generation
            solution_result = self.solution_agent.generate(vision_result)
            if not solution_result:
                print("Solution generation failed.")
                self.status_message = "Solution Failed"
                return
            
            # Save solution result
            self.last_solution_result = solution_result
            
            print(f"Solution: {solution_result.get('project_name')}")
            self.status_message = "Generating Preview..."
            self._push_event("processing", "Generating Preview Image...")
            
            # Step 3: Image Generation
            image_prompt = solution_result.get("image_prompt", "")
            preview_url = None
            if image_prompt:
                preview_url = self.image_agent.generate_image(image_prompt)
            
            if preview_url:
                print(f"Preview URL: {preview_url}")
                self.status_message = "Pipeline Complete! Check Console."
            else:
                self.status_message = "Pipeline Complete (No Image)."
            
            # Create final output
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
            
            # Push complete event
            self._push_event("complete", "Analysis Complete!", final_output)
            
        except Exception as e:
            print(f"AI Pipeline Error: {e}")
            self.status_message = "Error in Pipeline"
            self._push_event("error", str(e))
        finally:
            self.is_processing = False
    
    def run_ai_pipeline_async(self, image_path):
        """异步运行AI流程"""
        thread = threading.Thread(target=self.run_ai_pipeline, args=(image_path,))
        thread.daemon = True
        thread.start()
    
    def run_chat_ai(self, text):
        """
        运行对话AI
        
        Args:
            text: 用户输入文本
        """
        if self.is_processing:
            print("AI is busy, please wait.")
            self._push_event("voice_error", "AI正在忙碌，请稍后再试")
            return
        
        if not self.last_vision_result:
            print("No vision result to chat about. Please analyze an image first.")
            self.status_message = "Chat Failed: No Context"
            self._push_event("voice_error", "请先拍照分析图片")
            return
        
        self.is_processing = True
        self.status_message = "AI Thinking..."
        
        # 推送用户消息到前端
        self._push_event("voice_user", text, {"user_text": text})
        self._push_event("voice_processing", "AI正在思考...")
        
        try:
            print("\n--- Running Chat AI ---")
            print(f"[User]: {text}")
            
            # 使用chat()方法进行自然对话（而不是generate()生成完整方案）
            ai_response = self.solution_agent.chat(text)
            
            if ai_response:
                print(f"\n[AI Response]: {ai_response}")
                self.status_message = "AI Responded!"
                
                # 推送AI回复到前端
                print("📤 正在推送voice_response事件...")
                self._push_event("voice_response", ai_response, {
                    "ai_text": ai_response
                })
                print("✅ voice_response事件已推送")
            else:
                print("AI chat failed or returned no response.")
                self.status_message = "AI Chat Failed"
                self._push_event("voice_error", "AI回复失败")
        
        except Exception as e:
            print(f"Chat AI Error: {e}")
            self.status_message = "Error in Chat"
            self._push_event("voice_error", f"对话错误: {str(e)}")
        finally:
            self.is_processing = False
    
    def run_chat_ai_async(self, text):
        """异步运行对话AI"""
        thread = threading.Thread(target=self.run_chat_ai, args=(text,))
        thread.daemon = True
        thread.start()
    
    def transcribe_and_chat(self):
        """转录语音并进行对话"""
        if not self.voice_handler:
            print("Voice handler not available")
            self._push_event("voice_error", "语音模块不可用")
            return
        
        self._push_event("voice_processing", "正在转录语音...")
        
        text = self.voice_handler.transcribe_audio()
        if text:
            print(f"\n[Voice Command]: {text}\n")
            self.status_message = f"Voice: {text[:20]}..."
            self.run_chat_ai(text)
        else:
            print("Voice transcription failed or empty.")
            self.status_message = "Voice: No text"
            self._push_event("voice_error", "语音识别失败，请重试")
    
    def transcribe_and_chat_async(self):
        """异步转录语音并进行对话"""
        thread = threading.Thread(target=self.transcribe_and_chat)
        thread.daemon = True
        thread.start()
    
    def get_status(self):
        """获取当前状态"""
        return {
            "is_processing": self.is_processing,
            "status_message": self.status_message,
            "last_vision_result": self.last_vision_result,
            "last_solution_result": self.last_solution_result,
            "last_complete_result": self.last_complete_result
        }
    
    def is_busy(self):
        """检查AI是否繁忙"""
        return self.is_processing