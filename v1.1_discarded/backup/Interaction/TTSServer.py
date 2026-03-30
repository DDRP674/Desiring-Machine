import logging
import IPC
from lib_helper import load_json_with_comments
import threading

# 现在我他妈只支持流式传输了好吧
# 各个引擎直接将数据发向Live2D
# 对于音量数据，必须在Python端把音量先算好再发过去

class TTS_app:
    def __init__(self, show=True):
        self.show = show
        self.running = True

        self.ipc = IPC.BulletinClient("lib_tts2main")
        self.settings = load_json_with_comments("settings.json")["tts"]
        self.engine_name = self.settings["tts_engine"]

        if self.engine_name == "azure-tts": 
            import TTS.azure_tts
            self.engine = TTS.azure_tts.azure(self.show)

        threading.Thread(target=self.process, daemon=True).start()
            
    def logger(self, message):
        if self.show: logging.info(f"TTSServer.TTS_app: {message}")

    def process(self):
        while self.running:
            message = self.ipc.listen_earliest(receiver="TTSServer.process", timeout=-1)["messages"][0]["content"]
            if self.engine_name == "azure-tts":
                self.engine.speak(message)
                self.logger(f"已生成语音：{message}")

    def __del__(self):
        self.running = False

if __name__ == "__main__":
    pass