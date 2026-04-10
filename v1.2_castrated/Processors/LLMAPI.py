import json
import queue
import openai, os, logging
import sys
from threading import Lock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import load_json_with_comments, func_name

# 用于调用API的工具库。UI模块也可以调用它。

ATTRACTING_PROMPT = """
你在一个公共场所中被作为一个艺术展品展出。周围有许多人走过。
你的目标是，让任何一个人坐在你面前的椅子上。
而为了让人坐在那个椅子上，你会提供服务：{task_content}
现在你要说话来吸引这个公共场所中的人坐在椅子上。
例如：Can anyone sit on this chair? I can ...
注意：
1. 你上一次所说的是：{last_speech}，这次尽量更换口吻或方式。
2. 简短地说出自己的请求，使用简单的单词和语句，一句话最好，不可超过三句话。放在同一字符串下。
同时用中英文输出你要说的话，使用json格式：
{{"en": "English ver", "zh": "中文版本"}}
"""

KEEP_PROMPT_1 = """
你在一个公共场所中被作为一个艺术展品展出。
你的目标是，让任何一个人坐在你面前的椅子上并留住它。
现在一个人因为你提供了服务：{task_content} 而坐在了椅子上，但它要离开了。
你需要试图挽留它，但并不通过提供其他服务而挽留，而是继续提供原本的服务。你可以装可怜、道德绑架、假装恐吓等。
注意：
简短地说出自己的请求，使用简单的单词和语句，一句话最好，不可超过三句话。放在同一字符串下。
同时用中英文输出你要说的话，使用json格式：
{{"en": "English ver", "zh": "中文版本"}}
"""

KEEP_PROMPT_2 = """
你在一个公共场所中被作为一个艺术展品展出。
你的目标是，让任何一个人坐在你面前的椅子上并留住它。
现在一个人因为你提供了服务：{old_task_content} 而坐在了椅子上，但它要离开了。
你需要试图挽留它，而为此你打算放弃原本的服务，向提供新的服务：{new_task_content}
现在你需要生成你要说的话。例如：如果你不喜欢(原task)，没关系，我们可以(新task)
注意：
简短地说出自己的请求，使用简单的单词和语句，一句话最好，不可超过三句话。放在同一字符串下。
同时用中英文输出你要说的话，使用json格式：
{{"en": "English ver", "zh": "中文版本"}}
"""

class LLM:
    def __init__(self):
        self.processing_queue = queue.Queue()
        settingsPath = os.path.normpath("./settings.json")
        self.settings = load_json_with_comments(settingsPath)["llms"]
        self.attract_speech = ""

    def req(self, messagelist: list, settings: dict) -> dict:
        """调用原子"""
        try:
            client = openai.OpenAI(api_key=settings["api_key"], base_url=settings["api_base"])
            if settings.get("response_format", False):
                completion = client.chat.completions.create(
                    model=settings["model"],
                    messages=messagelist,
                    temperature=settings.get("temperature", 1.0),
                    response_format=settings["response_format"]
                )
            else:
                completion = client.chat.completions.create(
                    model=settings["model"],
                    messages=messagelist,
                    temperature=settings.get("temperature", 1.0)
                )
        except Exception as e:
            logging.warning(e)
            return {}
        return { "role": "assistant", "content": completion.choices[0].message.content }
    
    def Attract(self, task_content: str) -> dict: 
        """吸引"""
        self.attract_speech = self.req([{"role": "system", "content": ATTRACTING_PROMPT.format(
            task_content=task_content,
            last_speech=self.attract_speech if self.attract_speech else "无"
        )}], self.settings["LargeModelJson"]).get("content", "{}")
        return json.loads(self.attract_speech)

    def Keep1(self, task_content: str) -> dict: 
        """直接挽留"""
        return json.loads(self.req(
            [{"role": "system", "content": KEEP_PROMPT_1.format(task_content=task_content)}], 
            self.settings["LargeModelJson"]
        ).get("content", "{}"))

    def Keep2(self, old_task_content: str, new_task_content: str) -> dict:
        """改变策略地挽留"""
        return json.loads(self.req([{"role": "system", "content": KEEP_PROMPT_2.format(
                old_task_content=old_task_content,
                new_task_content=new_task_content
        )}], self.settings["LargeModelJson"]).get("content", "{}"))
    
if __name__ == "__main__":
    llm = LLM()
    a = llm.Keep1("Play Spongebob on the screen")
    print(a, type(a))
