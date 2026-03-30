import logging
import threading
import IPC, lib_helper

class Server:
    def __init__(self, show=True):
        self.show = show
        self.running = True
        self.ipc = IPC.BulletinClient("STTServer")
        self.settings = lib_helper.load_json_with_comments("settings.json")["stt"]
        self.engine_name = self.settings["stt_engine"]

        if self.engine_name == "tencent-asr":
            import STT.tencent_asr
            self.settings = self.settings["tencent-asr-settings"]
            self.engine = STT.tencent_asr.LiveTranscriber(self.settings, self.show)
            threading.Thread(target=self.engine.start, daemon=True).start()
            message = self.ipc.listen_earliest(sender=self.engine_name, receiver=self.ipc.client_name, timeout=120)["messages"]
            if not message: self.logger("tencent-asr引擎启动失败：未响应")
            if message[0]["content"] == "Done": self.logger("tencent-asr引擎启动成功")
            else: 
                m = message[0]["content"]
                self.logger(f"tencent-asr引擎启动失败：{m}")
        elif self.engine_name == "tencent-asr-onesentence":
            import STT.tencent_asr_onesentence
            self.settings = self.settings["tencent-asr-settings"]
            self.engine = STT.tencent_asr_onesentence.LiveTranscriber(self.settings, self.show)
            threading.Thread(target=self.engine.start, daemon=True).start()
            message = self.ipc.listen_earliest(sender=self.engine_name, receiver=self.ipc.client_name, timeout=120)["messages"]
            if not message: self.logger("tencent-asr引擎启动失败：未响应")
            if message[0]["content"] == "Done": self.logger("tencent-asr引擎启动成功")

        threading.Thread(target=self.engine_thread, daemon=True).start()

    def logger(self, message):
        if self.show: logging.info(f"STTServer.Server: {message}")
    
    def engine_thread(self):
        while self.running:
            result = self.engine_manager()
            self.ipc.post_message(receiver="LLM_main.process", content=result)

    def engine_manager(self):
        # 用于管理不同引擎的实际功能，这个函数仅接收一次消息并return
        if self.engine_name == "tencent-asr" or self.engine_name == "tencent-asr-onesentence":
            return self.engine_tencent_asr()

    def engine_tencent_asr(self):
        line = self.ipc.listen_earliest(sender=self.engine_name, receiver=self.ipc.client_name, timeout=-1)["messages"][0]
        message = ""
        if line["content"][:4] == "Msg:":
            message = line["content"][5:]
            self.logger(f"收到：\n{message}")
        elif line["content"][:4] == "Err:":
            message = line["content"][5:]
            self.logger(f"lib_stt2main.STT_app.engine_tencent_asr: 错误：\n{message}")
        return message
    
    def __del__(self):
        self.running = False
    
if __name__ == "__main__":
    a = Server()
    while True:
        print(a.engine_manager())

    