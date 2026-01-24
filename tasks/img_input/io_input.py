# -*- coding: utf-8 -*-
import sys
import signal
import Hobot.GPIO as GPIO
import time
import yaml  # 用于解析YAML配置文件

class GPIOButton:
    """
    一个模拟键盘按键行为的GPIO输入类。
    支持“状态查询”（是否被按下）和“事件驱动”（按一次触发一次）。
    """
    def __init__(self, input_pin, active_low=True, bouncetime=200):
        """
        初始化GPIO按键。
        :param input_pin: GPIO管脚编号 (BOARD编码).
        :param active_low: 如果为True，则低电平表示按下（使用内部上拉电阻）。
                           如果为False，则高电平表示按下（使用内部下拉电阻）。
        :param bouncetime: 消抖时间 (毫秒).
        """
        self.input_pin = input_pin
        self.active_low = active_low
        self._pressed_event = False
        self.last_press_time = 0
        self.cooldown = bouncetime / 1000.0  # 转换为秒

        # 只需要在程序开始时设置一次
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        # 根据active_low设置触发边缘
        if active_low:
            # Hobot.GPIO 可能不支持软件设置上下拉，移除 PUD_UP
            edge_to_detect = GPIO.FALLING
        else:
            # Hobot.GPIO 可能不支持软件设置上下拉，移除 PUD_DOWN
            edge_to_detect = GPIO.RISING

        # 移除 pull_up_down 参数
        GPIO.setup(self.input_pin, GPIO.IN)
        GPIO.add_event_detect(self.input_pin, edge_to_detect, callback=self._press_callback, bouncetime=bouncetime)
        # print(f"GPIO按键在管脚 {self.input_pin} 上已初始化。") # 在main函数中统一打印

    def _press_callback(self, channel):
        # 软件滤波：检查是否处于冷却时间内
        current_time = time.time()
        if current_time - self.last_press_time < self.cooldown:
            return

        # 简单的噪声过滤：再次检查电平状态
        # 如果是瞬间干扰，此时电平可能已经恢复
        if not self.is_pressed():
            return

        self.last_press_time = current_time
        self._pressed_event = True

    def is_pressed(self):
        if self.active_low:
            return GPIO.input(self.input_pin) == GPIO.LOW
        else:
            return GPIO.input(self.input_pin) == GPIO.HIGH

    def get_press(self):
        if self._pressed_event:
            self._pressed_event = False
            return True
        return False

    def cleanup(self):
        # The main cleanup is now handled globally by GPIO.cleanup()
        pass

def load_gpio_config(config_path):
    """
    加载并解析YAML配置文件。
    :param config_path: YAML配置文件的路径。
    :return: 包含GPIO配置的字典，或在出错时返回None。
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if not isinstance(config, dict):
                raise TypeError("配置文件内容不是有效的键值对格式。")
            return config
    except FileNotFoundError:
        print(f"错误：配置文件 '{config_path}' 未找到。")
        return None
    except yaml.YAMLError as e:
        print(f"错误：解析配置文件 '{config_path}' 时出错: {e}")
        return None
    except TypeError as e:
        print(f"错误：{e}")
        return None

def signal_handler(signal, frame):
    print("\n检测到Ctrl+C，正在退出...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    config_path = '/home/sunrise/SparkBox/config/io.yaml'
    buttons = {}
    
    try:
        # 1. 从YAML文件加载配置
        gpio_config = load_gpio_config(config_path)
        if not gpio_config:
            print("无法加载GPIO配置，程序退出。")
            return

        # 2. 根据配置分类管脚
        continuous_pins = {}
        single_shot_pins = {}
        
        for name, config in gpio_config.items():
            # 检查配置格式
            if not isinstance(config, dict) or 'pin' not in config:
                print(f"警告: 配置项 '{name}' 格式错误。应为 {{'pin': <int>, 'mode': <str>}}。已忽略。")
                continue
            
            pin = config.get('pin')
            mode = config.get('mode', 'single') # 默认为单次模式

            # 确保pin是整数
            if not isinstance(pin, int):
                print(f"警告: 配置项 '{name}' 的管脚值 '{pin}' 不是有效的整数。已忽略。")
                continue
            
            # 简单的 BOARD 模式管脚范围检查
            if pin < 1 or pin > 40:
                print(f"错误: 管脚编号 {pin} (用于 '{name}') 超出 BOARD 模式的有效范围 (1-40)。跳过此管脚。")
                continue

            # 根据 mode 分配
            if mode == 'continuous':
                continuous_pins[name] = pin
            elif mode == 'single':
                single_shot_pins[name] = pin
            else:
                print(f"警告: 配置项 '{name}' 的模式 '{mode}' 未知。仅支持 'continuous' 或 'single'。默认为 'single'。")
                single_shot_pins[name] = pin

        # 3. 打印分类结果
        print("--- GPIO 配置加载完成 ---")
        print("持续信号 (Continuous Signal) [按下持续触发]:")
        if continuous_pins:
            for name, pin in continuous_pins.items():
                print(f"  - {name}: Pin {pin}")
        else:
            print("  (无)")
        
        print("\n一次信号 (Single-shot Signal) [按一次触发一次]:")
        if single_shot_pins:
            for name, pin in single_shot_pins.items():
                print(f"  - {name}: Pin {pin}")
        else:
            print("  (无)")
        print("--------------------------\n")

        # 4. 初始化所有GPIOButton对象
        # 合并两个字典来初始化，避免重复代码
        all_pins = {**continuous_pins, **single_shot_pins}
        
        for name, pin in all_pins.items():
            try:
                # 获取该管脚的配置
                cfg = gpio_config.get(name, {})
                debounce = cfg.get('debounce', 200)
                buttons[name] = GPIOButton(input_pin=pin, bouncetime=debounce)
            except Exception as e:
                print(f"错误: 初始化管脚 {pin} ('{name}') 失败: {e}")
                # 初始化失败也要移除
                if name in continuous_pins:
                    del continuous_pins[name]
                if name in single_shot_pins:
                    del single_shot_pins[name]

        print("开始信号检测！请操作连接到GPIO的按键，或按 CTRL+C 退出。\n")
        
        # 5. 在主循环中根据信号类型处理
        # 记录所有管脚的上一次电平状态，用于检测“松开/复位”动作
        last_level_states = {name: False for name in all_pins.keys()}
        
        while True:
            # --- 处理“持续信号” ---
            for name in list(continuous_pins.keys()): 
                try:
                    is_pressed = buttons[name].is_pressed()
                    # 仅在状态改变时打印
                    if is_pressed != last_level_states.get(name, False):
                        state_str = "按下 (Active)" if is_pressed else "松开 (Inactive)"
                        print(f"[持续信号] '{name}' 状态更新: {state_str}")
                        last_level_states[name] = is_pressed
                except Exception as e:
                    print(f"错误: 读取 '{name}' 状态出错: {e}")
                    del continuous_pins[name]

            # --- 处理“一次信号” ---
            for name in list(single_shot_pins.keys()):
                try:
                    # 1. 检测按下事件 (触发动作)
                    if buttons[name].get_press():
                        print(f"[一次信号] '{name}' -> 触发信号 (Triggered)!")
                    
                    # 2. 监控复位状态 (可选，用于调试和确认)
                    # 我们也检查它的实时电平，以便知道它什么时候松开
                    current_pressed = buttons[name].is_pressed()
                    if current_pressed != last_level_states.get(name, False):
                        if not current_pressed:
                            # 之前是按下，现在是松开 -> 复位
                            print(f"[一次信号] '{name}' -> 已复位 (Reset/Released)")
                        last_level_states[name] = current_pressed
                        
                except Exception as e:
                    print(f"错误: 检测 '{name}' 出错: {e}")
                    del single_shot_pins[name]
            
            # 短暂休眠以降低CPU使用率
            time.sleep(0.05)

    except Exception as e:
        print(f"程序主循环发生未预料的错误: {e}")
    finally:
        # 在程序结束时执行全局清理
        GPIO.cleanup()
        print("\nGPIO资源已清理，程序已退出。")

if __name__ == '__main__':
    main()