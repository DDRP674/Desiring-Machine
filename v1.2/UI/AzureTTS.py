import azure.cognitiveservices.speech as speechsdk

class Engine:
    def __init__(self, settings: dict):
        self.settings = settings
        self.ssml = """
<speak version='1.0' 
        xmlns='http://www.w3.org/2001/10/synthesis' 
        xmlns:mstts="https://www.w3.org/2001/mstts"
        xml:lang="{lang}">
    <voice name="{voice_name}">
        <mstts:express-as style="{emotion}">
            <prosody rate='{speed}' pitch='{pitch}' volume='{volume}'>
                {text}
            </prosody>
        </mstts:express-as>
    </voice>
</speak>
"""
        self.parameters = {
            "lang": self.settings.get("language", "en-US"),
            "voice_name": self.settings.get("voice_name", "en-US-AshleyNeural"),
            "speed": self.settings.get("voice_speed", "medium"),
            "pitch": self.settings.get("voice_pitch", "+30Hz"),
            "volume": self.settings.get("voice_volume", "medium"),
            "emotion": "",
            "text": ""
        }
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.settings["api_key"], 
            region=self.settings["region"]
        )

    def speak(self, text: str):
        self.parameters["text"] = text
        ssml = self.ssml.format(**self.parameters)
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        self.synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config, 
            audio_config=audio_config
        )
        self.synthesizer.speak_ssml(ssml) # 阻塞的
