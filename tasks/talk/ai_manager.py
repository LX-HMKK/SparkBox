"""
AI管理器 - 负责AI流程管理、语音处理和AI pipeline协调
"""
import threading
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import urllib.request
import uuid


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

        # 日志目录
        base_dir = Path(__file__).resolve().parents[2]
        self.log_dir = base_dir / "logs" / "ai_logs"
        self.log_images_dir = self.log_dir / "images"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_images_dir.mkdir(parents=True, exist_ok=True)

        # 当前对话日志文件
        self.current_log_path = None

    def reset_results(self):
        """清空上一次结果，避免前端拉取到旧数据。"""
        self.last_vision_result = None
        self.last_solution_result = None
        self.last_complete_result = None
        self.status_message = "Ready"
        self.is_processing = False
    
    def set_event_callback(self, callback):
        """设置事件回调函数"""
        self.event_callback = callback
    
    def _push_event(self, state, message, data=None):
        """推送事件"""
        if self.event_callback:
            self.event_callback(state, message, data)

    def _get_log_file_path(self) -> Path:
        now = datetime.now()
        suffix = uuid.uuid4().hex[:6]
        filename = now.strftime(f"%Y-%m-%d_%H%M%S_{suffix}.json")
        return self.log_dir / filename

    def _start_new_log_session(self):
        """开启新的对话日志文件（一次对话对应一个文件）"""
        self.current_log_path = self._get_log_file_path()

    def _append_log_entries(self, entries: list):
        """追加日志条目，格式参照 ai_logs 日志"""
        if not self.current_log_path:
            self._start_new_log_session()

        log_path = self.current_log_path
        existing = []
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = []
            except Exception:
                existing = []

        existing.extend(entries)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def _log_text(self, role: str, content: str):
        if not content:
            return
        self._append_log_entries([
            {"role": role, "type": "text", "content": content}
        ])

    def _log_image(self, role: str, image_path_or_url: str, is_url: bool = False):
        if not image_path_or_url:
            return

        if is_url:
            local_path = self._download_image(image_path_or_url)
            if local_path:
                self._append_log_entries([
                    {"role": role, "type": "image", "content": local_path}
                ])
            return

        try:
            src_path = Path(image_path_or_url)
            if not src_path.exists():
                return

            target_name = src_path.name
            dest_path = self.log_images_dir / target_name

            if src_path.resolve() != dest_path.resolve():
                shutil.copy2(src_path, dest_path)

            rel_path = os.path.join("images", target_name)
            self._append_log_entries([
                {"role": role, "type": "image", "content": rel_path}
            ])
        except Exception as e:
            print(f"[AIManager] Log image failed: {e}")

    def _download_image(self, url: str) -> str | None:
        """下载URL图片到本地日志目录，返回相对路径"""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{ts}.jpg"
            dest_path = self.log_images_dir / filename

            with urllib.request.urlopen(url, timeout=20) as resp:
                content = resp.read()
                with open(dest_path, "wb") as f:
                    f.write(content)

            return os.path.join("images", filename)
        except Exception as e:
            print(f"[AIManager] Download image failed: {e}")
            return None

    def _format_solution_text(self, solution_result: dict) -> str:
        """将方案结果整理为分段要点，便于上位机展示"""
        if not solution_result:
            return ""

        parts = []
        name = solution_result.get("project_name") or solution_result.get("project_title")
        if name:
            parts.append(f"项目名称：{name}")

        core_idea = solution_result.get("core_idea")
        if core_idea:
            parts.append(f"核心思路：{core_idea}")

        materials = solution_result.get("materials")
        if materials:
            mat_str = "、".join(materials)
            parts.append(f"材料清单：{mat_str}")

        steps = solution_result.get("steps")
        if steps:
            step_lines = "\n".join([f"{idx+1}. {s}" for idx, s in enumerate(steps)])
            parts.append(f"制作步骤：\n{step_lines}")

        outcomes = solution_result.get("learning_outcomes")
        if outcomes:
            out_str = "\n".join([f"- {o}" for o in outcomes])
            parts.append(f"学习收获：\n{out_str}")

        return "\n\n".join(parts)
    
    def run_ai_pipeline(self, image_path):
        """
        运行AI流程
        
        Args:
            image_path: 图像路径
        """
        self.is_processing = True
        self.status_message = "Analyzing Image..."
        self._push_event("processing", "Analyzing Image...")

        # 新的一次分析视为新对话
        self._start_new_log_session()
        
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

            # 记录用户图片日志
            self._log_image("user", str(image_path))
            
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

            # 记录方案文本日志
            formatted_text = self._format_solution_text(solution_result)
            self._log_text("ai", formatted_text)
            
            print(f"Solution: {solution_result.get('project_name')}")
            self.status_message = "Generating Preview..."
            self._push_event("processing", "Generating Preview Image...")
            
            # Step 3: Image Generation
            image_prompt = solution_result.get("image_prompt", "")
            preview_url = None
            if image_prompt:
                preview_url = self.image_agent.generate_image(image_prompt)
                # 预取生成链接，避免前端首次加载时需要手动点开
                if preview_url:
                    self._prefetch_preview_url(preview_url)
            
            if preview_url:
                print(f"Preview URL: {preview_url}")
                self.status_message = "Pipeline Complete! Check Console."
                # 记录预览图日志（URL）
                self._log_image("ai", preview_url, is_url=True)
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

    def _prefetch_preview_url(self, url: str):
        """后台轻量请求一次预览图，确保前端无需手动打开即可开始加载"""
        def _fetch():
            try:
                print(f"[AIManager] Prefetch preview: {url}")
                # 只读取少量数据即可触发远端生成/缓存
                with urllib.request.urlopen(url, timeout=10) as resp:
                    resp.read(1024)
            except Exception as e:
                print(f"[AIManager] Prefetch failed: {e}")

        threading.Thread(target=_fetch, daemon=True).start()
    
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

        # 记录用户对话日志
        self._log_text("user", text)
        
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

                # 记录AI回复日志
                self._log_text("ai", ai_response)
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
        
        # Check for "null" string which indicates failure from voice2text
        if text and text.strip().lower() != "null":
            print(f"\n[Voice Command]: {text}\n")
            self.status_message = f"Voice: {text[:20]}..."
            self.run_chat_ai(text)
        else:
            print("Voice transcription failed or returned 'null'.")
            self.status_message = "Voice: Transcription Failed"
            self._push_event("voice_error", "语音识别失败，请再次输入")
    
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