from collections import deque
from datetime import datetime
import json
import logging
import zmq
import time
import threading
from lib_helper import load_json_with_comments

def format_timestamp(ts):
    """格式化时间戳为可读字符串"""
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def get_first_content(receive):
    return receive["messages"][0]["content"]

class BulletinBoardServer:
    def __init__(self, show=True):
        self.show = show

        self.context = zmq.Context()
        settings = load_json_with_comments("settings.json")["ipc"]

        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{settings['PUB-SUB']}")

        self.router_socket = self.context.socket(zmq.ROUTER)
        self.router_socket.bind(f"tcp://*:{settings['REQ-REP']}")

        self.messages = {}
        self.message_queue = deque(maxlen=settings["maxlen"])
        self.message_counter = 0
        self.lock = threading.Lock()
        self.running = True

        threading.Thread(target=self.run, daemon=True).start()
        self.logger("IPC: 公告板服务已启动 (ROUTER/DEALER模式)")

    def logger(self, message):
        if self.show: logging.info(message)

    def _send_router_response(self, identity, response):
        """确保发送单帧数据"""
        try:
            response_json = json.dumps(response).encode('utf-8')
            # 只发送数据帧（不发送空分隔帧）
            self.router_socket.send_multipart([identity, response_json])
        except Exception as e:
            logging.warning(f"发送响应失败: {e}")
            error_response = json.dumps({
                "status": "error", 
                "message": "Internal server error"
            }).encode('utf-8')
            self.router_socket.send_multipart([identity, error_response])

    def _store_message(self, sender, receiver, content):
        """存储消息并返回完整消息对象"""
        with self.lock:
            message_id = self.message_counter
            self.message_counter += 1
            
            message = {
                "id": message_id,
                "sender": sender,
                "receiver": receiver,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "is_broadcast": receiver.lower() == "all"
            }
            
            self.messages[message_id] = message
            self.message_queue.appendleft(message)
            return message

    def _message_matches_query(self, msg, query):
        """判断单个消息是否匹配查询条件"""
        if "sender" in query and msg["sender"] != query["sender"]:
            return False
        if "receiver" in query:
            if query["receiver"].lower() == "all" and not msg["is_broadcast"]:
                return False
            elif query["receiver"].lower() != "all" and msg["receiver"] != query["receiver"]:
                return False
        if "start_time" in query:
            msg_time = datetime.fromisoformat(msg["timestamp"])
            if msg_time < datetime.fromisoformat(query["start_time"]):
                return False
        if "end_time" in query:
            msg_time = datetime.fromisoformat(msg["timestamp"])
            if msg_time > datetime.fromisoformat(query["end_time"]):
                return False
        if "keyword" in query and query["keyword"].lower() not in msg["content"].lower():
            return False
        return True

    def _query_messages(self, query, remove=False):
        """查询消息，可选择是否删除"""
        with self.lock:
            results = []
            to_remove = []
            
            messages_to_check = reversed(self.message_queue) if query.get("latest_first") else self.messages.values()
            
            for msg in messages_to_check:
                if not self._message_matches_query(msg, query):
                    continue
                
                results.append(msg)
                if remove:
                    to_remove.append(msg["id"])
            
            if remove:
                for msg_id in to_remove:
                    if msg_id in self.messages:
                        del self.messages[msg_id]
                self.message_queue = deque(
                    [m for m in self.message_queue if m["id"] not in to_remove],
                    maxlen=self.message_queue.maxlen
                )
            
            return results

    def _fetch_recent_messages(self, k, query, reverse=False):
        """获取最近K条匹配的消息"""
        with self.lock:
            matches = []
            queue_to_check = reversed(self.message_queue) if not reverse else self.message_queue
            for msg in queue_to_check:
                if self._message_matches_query(msg, query):
                    matches.append((msg["id"], msg["timestamp"]))
            
            matches.sort(key=lambda x: x[1], reverse=not reverse)
            msg_ids_to_remove = [msg_id for msg_id, _ in matches[:k]]
            
            recent_messages = []
            new_queue = deque(maxlen=self.message_queue.maxlen)
            
            for msg in self.message_queue:
                if msg["id"] in msg_ids_to_remove:
                    recent_messages.append(msg)
                    if msg["id"] in self.messages:
                        del self.messages[msg["id"]]
                else:
                    new_queue.append(msg)
            
            self.message_queue = new_queue
            
            if reverse:
                recent_messages.sort(key=lambda x: x["timestamp"])
            return recent_messages

    request_list = []
    _request_list_lock = threading.Lock()  # 为request_list添加单独的锁

    def _handle_request(self, request):
        """处理所有类型的请求"""
        if self.show:
            with self._request_list_lock:
                self.request_list.append(request)
                if len(self.request_list) >= 2:
                    self.request_list = self.request_list[-2:]
                    if self.request_list[0] != self.request_list[1]: 
                        self.logger(f"IPC.BulletinBoardDerver._handle_request:\n{request}")
                else:
                    self.logger(f"IPC.BulletinBoardDerver._handle_request:\n{request}")
        
        action = request["action"]
        
        if action == "post":
            message = self._store_message(
                request["sender"],
                request["receiver"],
                request["content"]
            )
            
            # 发布消息不需要加锁，因为zmq的PUB-SUB套接字是线程安全的
            self.pub_socket.send_json({
                "event": "new_message",
                "message": message
            })
            
            return {
                "status": "success",
                "message_id": message["id"]
            }
        
        elif action == "fetch":
            messages = self._query_messages(request.get("query", {}), remove=True)
            return {
                "status": "success",
                "count": len(messages),
                "messages": messages
            }
        
        elif action == "query":
            messages = self._query_messages(request.get("query", {}), remove=False)
            return {
                "status": "success",
                "count": len(messages),
                "messages": messages
            }
        
        elif action == "fetch_recent":
            recent_messages = self._fetch_recent_messages(
                request.get("k", 1),
                request.get("query", {})
            )
            return {
                "status": "success",
                "count": len(recent_messages),
                "messages": recent_messages
            }
        
        elif action == "fetch_earliest":
            earliest_messages = self._fetch_recent_messages(
                request.get("k", 1),
                request.get("query", {}),
                reverse=True
            )
            return {
                "status": "success",
                "count": len(earliest_messages),
                "messages": earliest_messages
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }

    def run(self):
        self.logger("IPC: 公告板已启动")
        try:
            while self.running:
                try:
                    identity, raw_msg = self.router_socket.recv_multipart(flags=zmq.NOBLOCK)
                    
                    try:
                        request = json.loads(raw_msg.decode('utf-8'))
                        response = self._handle_request(request)
                        self._send_router_response(identity, response)
                    except (UnicodeDecodeError, json.JSONDecodeError) as e:
                        logging.warning(f"消息解码错误: {e}")
                        self._send_router_response(identity, {
                            "status": "error",
                            "message": "Invalid message format"
                        })
                    except KeyError as e:
                        logging.warning(f"缺少必要字段: {e}")
                        self._send_router_response(identity, {
                            "status": "error",
                            "message": f"Missing required field: {e}"
                        })
                    
                except zmq.Again:
                    time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger("正在关闭服务端...")
        finally:
            self.pub_socket.close()
            self.router_socket.close()
            self.context.term()

    def __del__(self):
        self.running = False



class BulletinClient:
    def __init__(self, client_name, listen=False, show=False):
        self.context = zmq.Context()
        self.client_name = client_name
        settings = load_json_with_comments("settings.json")["ipc"]
        
        # 订阅套接字
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://localhost:{settings['PUB-SUB']}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # 请求套接字（DEALER）
        self.dealer_socket = self.context.socket(zmq.DEALER)
        self.dealer_socket.setsockopt(zmq.IDENTITY, f"{client_name}_{time.time()}".encode())
        self.dealer_socket.connect(f"tcp://localhost:{settings['REQ-REP']}")
        
        self.running = True
        self.show = show
        self.message_callbacks = []
        
        if listen:
            self.thread = threading.Thread(target=self._listen_notifications, daemon=True)
            self.thread.start()

    def logger(self, message):
        if self.show: logging.info(f"IPC.BulletinClient({self.client_name}): {message}")

    def _parse_frames(self, frames):
        """处理多帧消息时的安全解析"""
        for frame in frames:
            try:
                data = json.loads(frame.decode('utf-8'))
                # 丢弃不符合基础结构的响应
                if isinstance(data, dict) and "status" in data:
                    return data
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return {"status": "error", "message": "Invalid response"}

    def _send_request(self, request):
        """统一发送请求并验证响应格式"""
        # 标记请求类型（关键改进）
        request_type = request["action"].split("_")[0]  # 提取'fetch'/'query'/'post'
        self.dealer_socket.send_json(request)
        
        # 接收响应时严格过滤
        while True:
            frames = self.dealer_socket.recv_multipart()
            response = self._parse_frames(frames)
            
            # 类型强制校验（新增）
            if not self._validate_response(response, request_type):
                continue
                
            # 统一字段填充（保证所有响应结构一致）
            response.setdefault("count", 0)
            response.setdefault("messages", [])
            return response

    def _validate_response(self, response, expected_type):
        """响应验证三大原则"""
        if response.get("status") != "success":
            return False
        # 原则1：post响应必须含message_id
        if expected_type == "post" and "message_id" not in response:
            return False
        # 原则2：fetch/query响应必须含count
        if expected_type in ("fetch", "query") and "count" not in response:
            return False
        # 原则3：禁止跨类型污染
        return not (
            (expected_type == "post" and "count" in response) or
            (expected_type != "post" and "message_id" in response)
        )

    def _listen_notifications(self):
        """监听通知消息 - 修改为阻塞模式"""
        while self.running:
            try:
                data = self.sub_socket.recv_json()  # 阻塞式接收
                if data["event"] == "new_message":
                    message = data["message"]
                    if message["receiver"].lower() == "all" or \
                    message["receiver"] == self.client_name:
                        for callback in self.message_callbacks:
                            callback(message)
            except Exception as e:
                if self.running:  # 只在运行状态下报告错误
                    logging.warning(f"通知接收错误: {e}")

    def register_callback(self, callback):
        """注册消息回调"""
        self.message_callbacks.append(callback)

    # 实用
    def post_message(self, receiver, content, sender=None):
        """发布消息"""
        if sender == None: sender = self.client_name
        return self._send_request({
            "action": "post",
            "sender": sender,
            "receiver": receiver,
            "content": content
        })

    def fetch_messages(self, **kwargs):
        """标准化fetch操作"""
        response = self._send_request({
            "action": "fetch",
            "query": self._build_query(**kwargs)
        })
        # 强制转换格式（双保险）
        return {
            "status": response["status"],
            "count": response["count"],
            "messages": response["messages"]
        }

    def query_messages(self, **kwargs):
        """标准化query操作"""
        response = self._send_request({
            "action": "query",
            "query": self._build_query(**kwargs)
        })
        # 确保不返回message_id字段
        return {k: v for k, v in response.items() if k != "message_id"}
    
    # 实用
    def query_latest_message(self, k=1, sender=None, receiver=None, 
                        start_time=None, end_time=None, keyword=None):
        """查询最晚发出的消息，不删除，不阻塞，未获取到就返回空消息"""
        query = self._build_query(sender, receiver, start_time, end_time, keyword)
        query["latest_first"] = True  # 确保按最新排序
        
        response = self._send_request({
            "action": "query",
            "query": query
        })
        
        # 返回最新消息或空列表
        if response.get("status") == "success" and response["count"] > 0:
            response["messages"] = response["messages"][:k]
            response["count"] = len(response["messages"])
        
        return response

    # 实用
    def fetch_recent_messages(self, k=1, sender=None, receiver=None,
                            start_time=None, end_time=None, keyword=None):
        """获取最近的K条消息"""
        query = self._build_query(sender, receiver, start_time, end_time, keyword)
        return self._send_request({
            "action": "fetch_recent",
            "k": k,
            "query": query
        })

    # 实用
    def fetch_earliest_messages(self, k=1, sender=None, receiver=None,
                              start_time=None, end_time=None, keyword=None):
        """获取最早的K条消息"""
        query = self._build_query(sender, receiver, start_time, end_time, keyword)
        return self._send_request({
            "action": "fetch_earliest",
            "k": k,
            "query": query
        })

    def _build_query(self, sender, receiver, start_time, end_time, keyword):
        """构建查询字典"""
        query = {}
        if sender: query["sender"] = sender
        if receiver: query["receiver"] = receiver
        if start_time: query["start_time"] = start_time.isoformat()
        if end_time: query["end_time"] = end_time.isoformat()
        if keyword: query["keyword"] = keyword
        return query

    def close(self):
        """关闭客户端"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        self.sub_socket.close()
        self.dealer_socket.close()
        self.context.term()

    response_list = []

    # 实用
    def listen_earliest(self, k=1, sender=None, receiver=None, 
                    start_time=None, end_time=None, keyword=None,
                    timeout=60): 
        """监听最初的k条消息 - 修正后的阻塞模式版本"""
        # 先尝试立即获取一次
        response = self.fetch_earliest_messages(
            k=k, sender=sender, receiver=receiver,
            start_time=start_time, end_time=end_time,
            keyword=keyword
        )
        
        self.logger(f"Initial response:\n{response}")
        
        if response.get("status") == "success" and response["count"] > 0:
            return response
        
        # 如果没有立即获取到，设置订阅并阻塞等待
        query = self._build_query(sender, receiver, start_time, end_time, keyword)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # 设置超时
        original_timeout = self.sub_socket.RCVTIMEO
        if timeout > 0:
            self.sub_socket.RCVTIMEO = int(timeout * 1000)  # 设置超时(毫秒)
        else:
            self.sub_socket.RCVTIMEO = -1  # 无限等待
        
        try:
            while self.running:
                try:
                    # 阻塞等待新消息
                    data = self.sub_socket.recv_json()
                    if data["event"] == "new_message":
                        # 检查新消息是否符合查询条件
                        message = data["message"]
                        if ((receiver is None or 
                            message["receiver"].lower() == "all" or 
                            message["receiver"] == receiver) and
                            (sender is None or message["sender"] == sender)):
                            # 再次尝试获取
                            response = self.fetch_earliest_messages(
                                k=k, sender=sender, receiver=receiver,
                                start_time=start_time, end_time=end_time,
                                keyword=keyword
                            )
                            if response.get("status") == "success" and response["count"] > 0:
                                return response
                except zmq.Again:
                    # 超时情况
                    return {
                        "status": "timeout",
                        "count": 0,
                        "messages": []
                    }
                except Exception as e:
                    if self.running:  # 只在运行状态下报告错误
                        logging.warning(f"监听过程中出错: {e}")
                        time.sleep(0.1)  # 防止错误循环占用CPU
                    
            # 正常退出循环(running=False)
            return {
                "status": "stopped",
                "count": 0,
                "messages": []
            }
        finally:
            # 恢复原始超时设置
            self.sub_socket.RCVTIMEO = original_timeout

    def close(self):
        self._running = False
        self.sub_socket.close()
        self.dealer_socket.close()
        self.context.term()

if __name__ == "__main__":
    server = BulletinBoardServer()

