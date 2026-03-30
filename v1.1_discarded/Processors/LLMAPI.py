import json
import openai, os, logging, IPC
import sys
from threading import Lock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import load_json_with_comments, func_name

# 用于调用API的工具库。UI模块也可以调用它。

COMPLETION_PROMPT_1 = """{Character}\n你的对话历史是：\n{FormattedSTM}"""
COMPLETION_PROMPT_2 = """现在你需要根据所给信息仔细检查并判断这一件事是否完成，
如果完成则返回True，未完成或不确定返回False，不应返回任何额外内容：
{FirstVolition}"""

VOLITIONGENERATION_PROMPT_1 = COMPLETION_PROMPT_1
# Prompt must contain the word 'json' in some form to use 'response_format' of type 'json_object'.
VOLITIONGENERATION_PROMPT_2 = """
现在你需要根据对话历史和人设等构建用于分层决策的意志树（注意，意志树不是决策树，它没有条件判断的功能）。请严格遵循以下规则：

核心任务：
根据已有对话信息，为当前目标生成一个树状结构的子意志。你可以生成任意层数，甚至只生成一层。
输入：一个明确的目标（当前目标），以及它的上级目标（作为辅助信息）。
输出：针对当前目标所生成的意志树的Json内容。你必须使用英文输出。
目前你只有说话的能力，你需要生成在你能力范围内的意志。并且，这些意志要与对话历史和人设等相符合。

生成规则：
1. 树状结构：每个意志节点包含内容、具体性判断、子意志数组
2. 具体性判断：
- `is_abstract: true` - 可以继续生长的意志，你可以给出它的子意志，也可以不给出。
- `is_abstract: false` - 足够具体、可直接执行的意志，它不能拥有子意志。
叶子意志不一定是具体的，也可以是抽象的。你所生成的所有叶子意志中，尽量要有至少一个可供生长的抽象叶子意志，除非特殊情况。

输出示例：
```json
{
"content": "根意志内容（当前目标）", "is_abstract": true,
"children": [
    { "content": "子意志1", "is_abstract": true/false, "children": [...] },
    { "content": "子意志2", "is_abstract": true/false, "children": [] }
]}"""
VOLITIONGENERATION_PROMPT_3 = """当前的目标是：{FirstVolition}，而上一级目标是{SecondVolition}。针对当前目标生成意志树。"""

class LLM:
    def __init__(self):
        settingsPath = os.path.normpath("settings.json")
        self.settings = load_json_with_comments(settingsPath)["llms"]
        self.ipc = IPC.BulletinClient("LLM")
        self.lock = Lock()

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
            logging.error(e)
            return {}
        return { "role": "assistant", "content": completion.choices[0].message.content }

    def Completeness(self, firstVolition: str) -> bool:
        """完成度检查"""
        with self.lock:
            dic = self.ipc.query_latest_message(sender="RobotState", receiver="Public")
        if not dic["messages"]: return False
        robotstate = json.loads(dic["messages"][0]["content"])
        STM = robotstate["STM"]
        FormattedSTM = ""
        for i in STM:
            if i["role"] == "assistant":
                FormattedSTM += "你："
            else:
                FormattedSTM += "用户："
            FormattedSTM += i["content"] + "\n"
        messagelist = []
        messagelist.append({"role": "system", "content": COMPLETION_PROMPT_1.format(
            Character=robotstate["Character"],
            FormattedSTM=FormattedSTM
        )})
        messagelist.append({"role": "user", "content": COMPLETION_PROMPT_2.format(
            FirstVolition=firstVolition # 这个并非来自于RobotState，而是直接由意志树给出
        )})
        res = self.req(messagelist, self.settings["Completion"])
        if not res: return False
        if "alse" in res["content"]: return False
        if "ure" in res["content"]: return True
        return False

    def GenerateVolitions(self, First2Volitions: list) -> dict: 
        """生成意志"""
        with self.lock:
            dic = self.ipc.query_latest_message(sender="RobotState", receiver="Public")
        if not dic["messages"]: return {}
        robotstate = json.loads(dic["messages"][0]["content"])
        STM = robotstate["STM"]
        FormattedSTM = ""
        for i in STM:
            if i["role"] == "assistant":
                FormattedSTM += "你："
            else:
                FormattedSTM += "用户："
            FormattedSTM += i["content"] + "\n"
        messagelist = []
        messagelist.append({"role": "system", 
            "content": VOLITIONGENERATION_PROMPT_1.format(
            Character=robotstate["Character"],
            FormattedSTM=FormattedSTM if FormattedSTM else "当前没有对话历史"
        )})
        messagelist.append({"role": "system", "content": VOLITIONGENERATION_PROMPT_2})
        if First2Volitions: FirstVolition = First2Volitions[0]
        else: FirstVolition = "Unknown"
        if len(First2Volitions) > 1: SecondVolition = First2Volitions[1]
        else: SecondVolition = "Unknown"
        messagelist.append({"role": "system", "content": VOLITIONGENERATION_PROMPT_3.format(
            FirstVolition=FirstVolition,
            SecondVolition=SecondVolition
        )})
        res = self.req(messagelist, self.settings["VolitionGeneration"])
        if type(res) == type(""):
            try: return res
            except json.JSONDecodeError as e: 
                logging.warning(f"{func_name()}: {e}")
                return {}
        else: return res
        
    def Chat(self) -> dict: # 待完成
        """UI模块调用的对话"""