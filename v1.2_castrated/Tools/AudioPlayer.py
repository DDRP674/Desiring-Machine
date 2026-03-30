import pygame
import threading

class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_sound = None
        self.is_playing = False
        self.volume = 1.0
    
    def play(self, audio_path, loop=False):
        """播放音频"""
        if self.is_playing:
            self.stop()
        
        try:
            self.current_sound = pygame.mixer.Sound(audio_path)
            loops = -1 if loop else 0
            self.current_sound.play(loops)
            self.is_playing = True
            self.current_sound.set_volume(self.volume)
            
            # 如果不是循环播放，启动监控线程
            if not loop:
                threading.Thread(target=self._wait_for_end, daemon=True).start()
                
        except Exception as e:
            print(f"播放失败: {e}")
    
    def _wait_for_end(self):
        """等待播放结束"""
        while pygame.mixer.get_busy() and self.is_playing:
            pygame.time.wait(500)
        self.is_playing = False
    
    def stop(self):
        """停止播放"""
        if self.current_sound:
            self.current_sound.stop()
        self.is_playing = False
    
    def set_volume(self, volume):
        """设置音量 0.0-1.0"""
        self.volume = volume

# 使用示例
if __name__ == "__main__":
    # pip install pygame
    
    player = AudioPlayer()
    
    # 播放音频
    player.play("assets/WAR/war.mp3")
    
    # 3秒后停止
    import time
    time.sleep(5)
    player.stop()
    time.sleep(5)
    
    # 播放循环背景音乐
    # player.play("background.mp3", loop=True)
    
    # 设置音量
    player.set_volume(0.5)