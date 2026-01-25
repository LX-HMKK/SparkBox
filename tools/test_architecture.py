"""
测试优化后的架构 - 不依赖外部硬件和API
"""
import sys
from pathlib import Path

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent
TASKS_DIR = BASE_DIR / "tasks"

# Add task directories to sys.path to allow imports
sys.path.append(str(TASKS_DIR / "img_input"))
sys.path.append(str(TASKS_DIR / "talk"))
sys.path.append(str(TASKS_DIR / "ui_output"))

def test_imports():
    """测试模块导入"""
    print("Testing imports...")
    
    try:
        from camera_manager import CameraManager
        print("✓ CameraManager imported successfully")
    except Exception as e:
        print(f"✗ CameraManager import failed: {e}")
    
    try:
        from ai_manager import AIManager
        print("✓ AIManager imported successfully")
    except Exception as e:
        print(f"✗ AIManager import failed: {e}")
    
    try:
        from web_manager import WebManager
        print("✓ WebManager imported successfully")
    except Exception as e:
        print(f"✗ WebManager import failed: {e}")

def test_camera_manager():
    """测试摄像头管理器"""
    print("\nTesting CameraManager...")
    
    try:
        from camera_manager import CameraManager
        
        # 创建管理器实例
        camera_mgr = CameraManager(camera_id=0)
        print("✓ CameraManager instance created")
        
        # 测试状态更新
        camera_mgr.update_status("Test message", is_processing=True)
        print(f"✓ Status updated: {camera_mgr.status_message}")
        
        print("✓ CameraManager tests passed")
    except Exception as e:
        print(f"✗ CameraManager test failed: {e}")

def test_ai_manager():
    """测试AI管理器"""
    print("\nTesting AIManager...")
    
    try:
        from ai_manager import AIManager
        
        # 创建模拟配置和代理
        global_config = {"test": True}
        
        # 模拟代理类
        class MockAgent:
            def __init__(self, config):
                self.config = config
            
            def analyze(self, path):
                return {"result": "mock_vision"}
            
            def generate(self, data, user_message=None):
                return {"result": "mock_solution"}
            
            def generate_image(self, prompt):
                return "mock_image_url"
        
        # 创建管理器
        ai_mgr = AIManager(
            global_config,
            MockAgent(global_config),  # vision_agent
            MockAgent(global_config),  # solution_agent
            MockAgent(global_config)   # image_agent
        )
        print("✓ AIManager instance created")
        
        # 测试状态
        status = ai_mgr.get_status()
        print(f"✓ Status retrieved: {status['status_message']}")
        
        print("✓ AIManager tests passed")
    except Exception as e:
        print(f"✗ AIManager test failed: {e}")

def test_web_manager():
    """测试Web管理器"""
    print("\nTesting WebManager...")
    
    try:
        from web_manager import WebManager
        
        # 创建临时文件夹路径
        templates_folder = str(TASKS_DIR / "ui_output" / "templates")
        static_folder = str(TASKS_DIR / "ui_output" / "static")
        
        # 创建管理器
        web_mgr = WebManager(templates_folder, static_folder, port=5001)
        print("✓ WebManager instance created")
        
        # 测试事件推送
        web_mgr.push_event("test", "Test message")
        print("✓ Event pushed successfully")
        
        print("✓ WebManager tests passed")
    except Exception as e:
        print(f"✗ WebManager test failed: {e}")

def main():
    """主测试函数"""
    print("=" * 50)
    print("Architecture Test Suite")
    print("=" * 50)
    
    test_imports()
    test_camera_manager()
    test_ai_manager()
    test_web_manager()
    
    print("\n" + "=" * 50)
    print("Architecture validation complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()