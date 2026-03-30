import logging
import sys, os, collections, random
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import get_filename
import Tools.VideoPlayer as VideoPlayer
import Tools.AudioPlayer as AudioPlayer

VP = VideoPlayer.FFplayPlayer()
AP = AudioPlayer.AudioPlayer()
AP.set_volume(0.6)
MAP = {"3": "./assets/MUSIC", "10": "./assets/XYJ"}

class VideoManager:
    def __init__(self, dir): 
        # e.g. dir="./assets/AZMG"
        # AZMG, DLZM, MEME, ROCKET, SB, XYJ
        self.dir = os.path.normpath(dir)
        self.videos = sorted(get_filename(self.dir))
        self.videos = collections.deque([os.path.join(self.dir, i) for i in self.videos])
        self.keep1 = {}
        self.running = False
        
    def play_one(self):
        """播放一个并阻塞"""
        path = self.videos.popleft()
        VP.play(path)
        self.videos.append(path)
        VP.wait_until_finished(path)
        VP.stop()
        
    def playthread(self):
        while self.running: self.play_one()

    def do(self): 
        """一直播放"""
        self.running = True
        threading.Thread(target=self.playthread, daemon=True).start()

    def stop(self):
        VP.stop()
        self.running = False

class AudioManager:
    def __init__(self, dir):
        # WAR MUSIC SE RAIN
        self.dir = os.path.normpath(dir)
        self.audios = [os.path.join(self.dir, path) for path in get_filename(self.dir)]
        self.keep1 = {}
        self.running = False

    def play(self):
        """播放一个"""
        while self.running:
            AP.play(random.choices(self.audios, k=1)[0])
            self.running = True
            AP._wait_for_end()
            AP.stop()

    def do(self): # 待完成
        """一直播放"""
        self.running = True
        threading.Thread(target=self.play, daemon=True).start()

    def stop(self):
        AP.stop()
        self.running = False

class FakeManager:
    def __init__(self, content): 
        self.content = content 
        self.running = False
        self.keep1 = {}

    def do(self): 
        logging.info(f"Do: {self.content}")
        self.running = True

    def stop(self): 
        logging.info(f"Stop: {self.content}")
        self.running = False

Managers = {
    # "1": VideoManager(MAP["1"]),
    # "2": VideoManager(MAP["2"]),
    "3": AudioManager(MAP["3"]),
    # "4": AudioManager(MAP["4"]),
    # "5": VideoManager(MAP["5"]),
    # "6": VideoManager(MAP["6"]),
    # "7": AudioManager(MAP["7"]),
    # "8": VideoManager(MAP["8"]),
    # "9": AudioManager(MAP["9"]),
    "10": VideoManager(MAP["10"]),
    # "11": VideoManager(MAP["11"])
}

# Managers = dict([(str(i), FakeManager(MAP[str(i)])) for i in range(1,11)])

if __name__ == "__main__": 
    import time
    a = Managers["3"]
    a.do()
    input()
    a.stop()
    time.sleep(3)