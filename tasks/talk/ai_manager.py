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
            return
        
        if not self.last_vision_result:
            print("No vision result to chat about. Please analyze an image first.")
            self.status_message = "Chat Failed: No Context"
            return
        
        self.is_processing = True
        self.status_message = "AI Thinking..."
        
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
                print(json.dumps(new_solution, indent=2, ensure_ascii=False))
                self.status_message = "AI Responded!"
            else:
                print("AI chat failed or returned no response.")
                self.status_message = "AI Chat Failed"
        
        except Exception as e:
            print(f"Chat AI Error: {e}")
            self.status_message = "Error in Chat"
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
            return
        
        text = self.voice_handler.transcribe_audio()
        if text:
            print(f"\n[Voice Command]: {text}\n")
            self.status_message = f"Voice: {text[:20]}..."
            self.run_chat_ai(text)
        else:
            print("Voice transcription failed or empty.")
            self.status_message = "Voice: No text"
            self._push_event("error", "Voice transcription failed")
    
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