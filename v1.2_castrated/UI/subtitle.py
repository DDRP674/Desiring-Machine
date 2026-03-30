import logging
import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush

class ThreadSafeSubtitle(QObject):
    """线程安全的字幕更新类"""
    update_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.window = None
    
    def create_window(self, text="字幕框"):
        """创建窗口（必须在主线程调用）"""
        self.window = SubtitleWindow(text)
        self.update_signal.connect(self.window.update_text)
        return self.window
    
    def update_text(self, text):
        """线程安全的文本更新方法"""
        if self.window and self.update_signal:
            self.update_signal.emit(text)

class SubtitleWindow(QWidget):
    def __init__(self, text="字幕框"):
        super().__init__()
        self.dragging = False
        self.offset = QPoint()
        
        # 窗口设置
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 字体
        self.font = QFont("Microsoft YaHei", 24)
        
        # 文本标签
        self.label = QLabel(text, self)
        self.label.setFont(self.font)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 180);
                padding: 10px 20px;
                border-radius: 5px;
            }
        """)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        
        # 根据文本调整大小
        self.adjust_size(text)
        
        # 初始位置
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() // 2 - self.width() // 2, screen.height() // 2 - self.height() // 2)
    
    def adjust_size(self, text):
        """根据文本调整窗口大小"""
        # 记录当前窗口中心位置
        center = self.mapToGlobal(self.rect().center())
        
        # 临时设置文本以计算大小
        self.label.setText(text)
        
        # 计算合适的大小
        self.label.adjustSize()
        label_width = min(self.label.width(), 8000) 
        label_height = self.label.height()
        
        # 设置窗口大小
        self.resize(label_width, label_height)
        
        # 以中心位置为基准重新定位窗口
        self.move(center.x() - label_width // 2, center.y() - label_height // 2)
    
    def update_text(self, text):
        """更新文本"""
        try:
            try:
                self.adjust_size(text)
                self.label.setText(text)
            except KeyboardInterrupt:
                self.adjust_size(text)
                self.label.setText(text)
        except: logging.info("锟斤拷")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    def paintEvent(self, event):
        """绘制透明背景"""
        try:
            painter = QPainter(self)
            painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # 完全透明
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())
        except KeyboardInterrupt: 
            painter = QPainter(self)
            painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # 完全透明
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())
    
    def exit(self):
        """退出函数"""
        self.close()
        QApplication.quit()

app = QApplication(sys.argv)
# 使用示例
if __name__ == "__main__":
    
    
    # 创建线程安全的字幕管理器
    subtitle_manager = ThreadSafeSubtitle()
    
    # 创建窗口
    window = subtitle_manager.create_window("字幕框启动中...")
    window.show()
    
    # 模拟从其他线程更新字幕
    def update_from_thread():
        import threading
        import time
        
        def update_task():
            texts = [
                "第一句话",
                "这是一段中等长度的文本，会换行显示这是一段中等长度的文本，会换行显示这是一段中等长度的文本，会换行显示",
                "短",
                "多行文本\n第二行\n第三行\n第四行"
            ]
            
            for i, text in enumerate(texts):
                time.sleep(2)
                print(f"从线程更新: {text[:20]}...")
                subtitle_manager.update_text(text)
        
        thread = threading.Thread(target=update_task, daemon=True)
        thread.start()
    
    # 2秒后开始更新
    QTimer.singleShot(2000, update_from_thread)
    
    print("字幕框已启动（可拖动，支持多线程更新）")
    sys.exit(app.exec_())