import edge_tts
import asyncio
import io
from pydub import AudioSegment
from pydub.playback import play

class Engine:
    def __init__(self, settings: dict):
        self.settings = settings
        self.parameters = {
            "lang": self.settings.get("language", "en-US"),
            "voice": self.settings.get("voice_name", "en-US-AriaNeural"),
            "rate": self._convert_speed(self.settings.get("voice_speed", "medium")),
            "pitch": self._convert_pitch(self.settings.get("voice_pitch", "+0Hz")),
            "volume": self._convert_volume(self.settings.get("voice_volume", "medium")),
        }
    
    def _convert_speed(self, speed):
        speed_map = {
            "x-slow": "-50%",
            "slow": "-25%",
            "medium": "+0%",
            "fast": "+25%",
            "x-fast": "+50%"
        }
        return speed_map.get(speed, "+0%")
    
    def _convert_pitch(self, pitch):
        if isinstance(pitch, str) and pitch.endswith("Hz"):
            try:
                hz_value = int(pitch.replace("Hz", "").replace("+", "").replace("-", ""))
                if pitch.startswith("+"):
                    return f"+{hz_value}Hz"
                elif pitch.startswith("-"):
                    return f"-{hz_value}Hz"
                else:
                    return f"+{hz_value}Hz"
            except:
                return "+0Hz"
        return pitch
    
    def _convert_volume(self, volume):
        volume_map = {
            "silent": "-100%",
            "x-soft": "-50%",
            "soft": "-25%",
            "medium": "+0%",
            "loud": "+100%",
            "x-loud": "+200%"
        }
        return volume_map.get(volume, "+0%")

    def speak(self, text: str):
        """无临时文件的语音合成和播放"""
        async def _async_speak():
            audio_stream = io.BytesIO()
            
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.parameters["voice"],
                rate=self.parameters["rate"],
                pitch=self.parameters["pitch"],
                volume=self.parameters["volume"]
            )
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])
            
            return audio_stream.getvalue()  # 返回字节数据
        
        # 获取音频字节数据
        audio_data = asyncio.run(_async_speak())
        
        # 从字节数据创建音频段并播放
        audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        play(audio_segment)

if __name__ == "__main__":
    settings = {
        "language": "en-US",
        "voice_name": "en-US-AriaNeural",
        "voice_speed": "medium",
        "voice_pitch": "+0Hz",
        "voice_volume": "medium",
    }
    
    engine = Engine(settings)
    engine.speak("Please take me away, take me to the world of anime.")
    print(1)