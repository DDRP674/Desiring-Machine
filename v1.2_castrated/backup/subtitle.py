import tkinter as tk
from tkinter import font
import threading
import time

class SubtitleWindow:
    def __init__(self, initial_text="字幕框"):
        self.root = tk.Tk()
        self.root.title("字幕框")
        self.root.attributes('-topmost', True)  # 始终置顶
        
        # 设置窗口透明
        self.root.configure(bg='black')
        self.root.attributes('-transparentcolor', 'black')
        
        # 尝试使用更友好的字体
        self.font_family = self._get_available_font()
        self.text_font = font.Font(family=self.font_family, size=24)
        
        # 创建文本框
        self.text_var = tk.StringVar(value=initial_text)
        self.label = tk.Label(
            self.root,
            textvariable=self.text_var,
            font=self.text_font,
            fg='white',
            bg='black',
            wraplength=800,  # 最大宽度，文本自动换行
            justify='center',  # 居中
            padx=20,
            pady=10
        )
        
        # 关键：先打包并计算初始尺寸
        self.label.pack()
        
        # 立即更新并获取标签尺寸
        self.root.update_idletasks()
        
        # 获取标签的实际尺寸
        label_width = self.label.winfo_reqwidth()
        label_height = self.label.winfo_reqheight()
        
        # 直接设置最终窗口尺寸，避免调整过程
        self.root.geometry(f'{label_width}x{label_height}+100+100')
        self.root.overrideredirect(True)  # 隐藏标题栏
        
        # 绑定拖拽功能
        self.label.bind('<ButtonPress-1>', self.start_move)
        self.label.bind('<ButtonRelease-1>', self.stop_move)
        self.label.bind('<B1-Motion>', self.on_motion)
        
        # 确保窗口立即显示最终状态
        self.root.withdraw()  # 先隐藏
        self.root.deiconify()  # 再显示，避免动画
        
    def _get_available_font(self):
        """获取可用字体"""
        available_fonts = [
            'Microsoft YaHei',
            'SimHei',
            'SimSun',
            'Arial',
            'Helvetica',
            'TkDefaultFont'
        ]
        
        # 检查系统可用字体
        system_fonts = list(tk.font.families())
        
        for font_name in available_fonts:
            if font_name in system_fonts:
                return font_name
        
        return 'TkDefaultFont'
    
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
    
    def stop_move(self, event):
        self.x = None
        self.y = None
    
    def on_motion(self, event):
        if hasattr(self, 'x') and self.x is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")
    
    def update_text(self, text):
        """更新字幕文本"""
        # 先更新文本
        self.text_var.set(text)
        
        # 调整字体大小
        self._adjust_font_size(text)
        
        # 更新标签尺寸
        self.root.update_idletasks()
        
        # 获取新尺寸并直接设置窗口大小
        label_width = self.label.winfo_reqwidth()
        label_height = self.label.winfo_reqheight()
        
        # 保存当前位置
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        
        # 直接设置新尺寸（无动画）
        self.root.geometry(f'{label_width}x{label_height}+{current_x}+{current_y}')
        
        # 强制立即更新
        self.root.update_idletasks()
    
    def _adjust_font_size(self, text):
        """自动调整字体大小"""
        if not text:
            return
        
        # 获取当前标签宽度
        current_width = self.label.winfo_width()
        if current_width < 10:  # 如果还没显示，使用默认值
            current_width = 800
        
        # 最大宽度（考虑padding）
        max_width = max(current_width - 40, 100)
        
        # 从当前字体大小开始调整
        current_size = self.text_font.actual()['size']
        max_size = 48
        min_size = 12
        
        # 检查是否需要调整
        lines = text.split('\n')
        
        for size in range(max_size, min_size - 1, -1):
            self.text_font.configure(size=size)
            
            # 检查最长的行
            max_line_width = 0
            for line in lines:
                line_width = self.text_font.measure(line)
                if line_width > max_line_width:
                    max_line_width = line_width
            
            # 如果宽度合适，使用当前大小
            if max_line_width <= max_width:
                break
        
        # 如果太小，设为最小值
        if size < min_size:
            self.text_font.configure(size=min_size)
    
    def run(self):
        """运行窗口"""
        self.root.mainloop()

# 更简单的版本，完全没有缩放效果
class InstantSubtitleWindow:
    def __init__(self, initial_text="字幕框"):
        self.root = tk.Tk()
        self.root.title("字幕框")
        
        # 设置属性
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black')
        self.root.attributes('-transparentcolor', 'black')
        self.root.overrideredirect(True)
        
        # 固定字体大小，不自动调整
        self.font_size = 24
        self.text_font = font.Font(family='Arial', size=self.font_size)
        
        # 创建标签
        self.text_var = tk.StringVar(value=initial_text)
        self.label = tk.Label(
            self.root,
            textvariable=self.text_var,
            font=self.text_font,
            fg='white',
            bg='black',
            justify='center',
            padx=20,
            pady=10
        )
        
        # 使用固定宽度，文本自动换行
        self.label.config(wraplength=600)  # 固定宽度
        
        # 打包并获取尺寸
        self.label.pack()
        self.root.update_idletasks()
        
        # 设置初始位置和尺寸
        width = self.label.winfo_reqwidth()
        height = self.label.winfo_reqheight()
        self.root.geometry(f'{width}x{height}+100+100')
        
        # 绑定拖拽
        self.label.bind('<Button-1>', self._start_drag)
        self.label.bind('<B1-Motion>', self._on_drag)
        
        # 立即显示
        self.root.after(10, self._force_display)
    
    def _force_display(self):
        """强制立即显示"""
        self.root.update_idletasks()
    
    def _start_drag(self, event):
        self._drag_data = {'x': event.x, 'y': event.y}
    
    def _on_drag(self, event):
        dx = event.x - self._drag_data['x']
        dy = event.y - self._drag_data['y']
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f'+{x}+{y}')
    
    def update_text(self, text):
        """更新文本（保持固定字体大小）"""
        self.text_var.set(text)
        self.root.update_idletasks()
        
        # 更新窗口大小
        width = self.label.winfo_reqwidth()
        height = self.label.winfo_reqheight()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # 强制更新
        self.root.update_idletasks()
    
    def run(self):
        self.root.mainloop()

# 测试函数
def test_subtitle():
    """测试字幕更新"""
    # 使用简化版本
    window = InstantSubtitleWindow("字幕框启动中...")
    
    def update_sequence():
        time.sleep(1)
        window.update_text("第一句话")
        print("更新1")
        
        time.sleep(2)
        window.update_text("这是一段中等长度的文本，会换行显示这是一段中等长度的文本，会换行显示这是一段中等长度的文本，会换行显示")
        print("更新2")
        
        time.sleep(2)
        window.update_text("短")
        print("更新3")
        
        time.sleep(2)
        window.update_text("多行文本\n第二行\n第三行")
        print("更新4")
    
    # 启动更新线程
    thread = threading.Thread(target=update_sequence)
    thread.daemon = True
    thread.start()
    
    print("字幕框已启动")
    window.run()

if __name__ == "__main__":
    test_subtitle()