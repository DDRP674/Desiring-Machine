import os, sys, pyttsx3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import load_json_with_comments

class TTS_app:
    def __init__(self): 
        self.settings = load_json_with_comments("settings.json").get("stt", {})
        if self.settings.get("engine", "") == "pyttsx3": pass
        elif self.settings.get("engine", "") == "edge_tts": 
            import UI.EdgeTTS
            self.engine = UI.EdgeTTS.Engine(self.settings["settings"]["edge_tts"])

    def Speak(self, content: str) -> None:
        if self.settings.get("engine", "") == "pyttsx3":
            # 用 Windows 自带的语音 API
            try:
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(content)
            except:
                # 如果失败，用回原来的方法但加上延迟
                engine = pyttsx3.init()
                engine.say(content)
                engine.runAndWait()
                
        elif self.settings.get("engine", "") == "edge_tts": 
            self.engine.speak(content)

if __name__ == "__main__":
    tts = TTS_app()
    tts.Speak("A person who thinks all the time")
    tts.Speak("Has nothing to think about except thoughts")