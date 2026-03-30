import os, sys, pyttsx3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import load_json_with_comments

class TTS_app:
    def __init__(self): 
        self.settings = load_json_with_comments("settings.json").get("stt", {})
        if self.settings.get("engine", "") == "pyttsx3": pass
        elif self.settings.get("engine", "") == "azure_tts": 
            import UI.AzureTTS
            self.engine = UI.AzureTTS.Engine(self.settings["settings"]["azure_tts"])
        elif self.settings.get("engine", "") == "edge_tts": 
            import UI.EdgeTTS
            self.engine = UI.EdgeTTS.Engine(self.settings["settings"]["edge_tts"])

    def Speak(self, content: str) -> None:
        """弄一个会阻塞线程的实现"""
        if self.settings.get("engine", "") == "pyttsx3":
            self.engine = pyttsx3.init() # 要每次都初始化，我也不知道为啥
            self.engine.say(content)
            self.engine.runAndWait()
        elif self.settings.get("engine", "") == "azure_tts": self.engine.speak(content)
        elif self.settings.get("engine", "") == "edge_tts": self.engine.speak(content)