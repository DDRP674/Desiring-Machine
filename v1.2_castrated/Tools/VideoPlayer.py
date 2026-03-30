import subprocess
import signal, time
import os

class FFplayPlayer:
    """使用ffplay，可以完全控制进程"""
    def __init__(self):
        self.process = None
        
    def play(self, video_path, autoclose=True, fullscreen=True):
        """使用ffplay播放（推荐安装ffmpeg）"""
        video_path = os.path.abspath(video_path)
        try:
            # 检查ffplay是否可用
            result = subprocess.run(['ffplay', '-version'], 
                                capture_output=True, text=True)
            if result.returncode != 0:
                print("未找到ffplay，请安装ffmpeg")
                return False
            
            # 构建命令
            cmd = ['ffplay', '-i', video_path, '-autoexit']
            if not autoclose:
                cmd = ['ffplay', '-i', video_path]
            if fullscreen: cmd.append('-fs')
            
            # 添加音量控制参数：将音量设置为30%（原音量的30%）
            cmd.extend(['-volume', '30'])
            
            # 启动ffplay
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            print(f"FFplay播放中 (PID: {self.process.pid})")
            return True
            
        except FileNotFoundError:
            print("请先安装ffmpeg并添加ffplay到PATH")
            return False
        except Exception as e:
            print(f"播放失败: {e}")
            return False
        
    def is_playing(self):
        """检查是否正在播放"""
        if self.process is None: return False
        return self.process.poll() is None
    
    def wait_until_finished(self, video_path, cooldown=0.5):
        """阻塞直到播放结束"""
        start = time.time()
        duration = self.get_duration(video_path)
        while time.time()-start < duration:
            if not self.is_playing: break
            time.sleep(cooldown)

    def get_duration(self, video_path):
        """获取视频总时长（秒）"""
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries',
                'format=duration', '-of',
                'default=noprint_wrappers=1:nokey=1', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except: pass
        return None
    
    def stop(self):
        """停止ffplay"""
        if self.process:
            # 发送Ctrl+C信号
            self.process.send_signal(signal.CTRL_C_EVENT)
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            print("已停止FFplay")
            return True
        return False
    
if __name__ == "__main__": pass