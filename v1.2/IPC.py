import redis
import json
import logging
import time
import threading
import uuid
from typing import List, Dict, Any, Optional, Callable

def clear_ipc_data(host='localhost', port=6379, db=0):
    r = redis.Redis(host=host, port=port, db=db)
    keys = r.keys("ipc:*")
    if keys:
        r.delete(*keys)
    r.set("ipc:message_counter", 0)
    print("IPC数据已清空")

class RedisIPCServer:
    def __init__(self, host='localhost', port=6379, db=0, maxlen=1000, show=True, clear_on_start=True):
        if clear_on_start:
            clear_ipc_data(host, port, db)
        
        self.show = show
        self.running = True
        self.maxlen = maxlen
        
        # Redis 连接
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        
        # 测试连接
        try:
            self.redis_client.ping()
        except redis.ConnectionError:
            logging.error("无法连接到Redis服务器")
            raise
        
        self.message_counter_key = "ipc:message_counter"
        
        # 初始化计数器
        if not self.redis_client.exists(self.message_counter_key):
            self.redis_client.set(self.message_counter_key, 0)
        
        # 启动请求处理线程
        threading.Thread(target=self._process_requests, daemon=True).start()
        self.logger("Redis IPC: 服务已启动 (兼容模式)")

    def logger(self, message):
        if self.show: 
            logging.info(message)

    def _get_next_message_id(self):
        """获取下一个消息ID"""
        return self.redis_client.incr(self.message_counter_key)

    def _store_message(self, sender: str, receiver: str, content: str) -> Dict[str, Any]:
        """存储消息到Redis List"""
        message_id = self._get_next_message_id()
        message = {
            "id": message_id,
            "sender": sender,
            "receiver": receiver,
            "content": content,
            "timestamp": time.time(),
            "is_broadcast": receiver.lower() == "all"
        }
        
        message_json = json.dumps(message)
        
        # 存储到接收者的频道
        channel_key = f"ipc:channel:{receiver}"
        self.redis_client.lpush(channel_key, message_json)
        
        # 限制列表长度
        self.redis_client.ltrim(channel_key, 0, self.maxlen - 1)
        
        # 同时存储到广播频道
        if receiver.lower() != "all":
            broadcast_key = "ipc:channel:all"
            self.redis_client.lpush(broadcast_key, message_json)
            self.redis_client.ltrim(broadcast_key, 0, self.maxlen - 1)
        
        # 发布新消息通知
        self.redis_client.publish("ipc:notifications", json.dumps({
            "event": "new_message",
            "message": message
        }))
        
        self.logger(f"消息已存储: {sender} -> {receiver} (ID: {message_id})")
        return message

    def _query_latest(self, receiver: str) -> Optional[Dict[str, Any]]:
        """查询指定频道的最新消息（列表的第一个元素）"""
        channel_key = f"ipc:channel:{receiver}"
        
        if not self.redis_client.exists(channel_key):
            return None
            
        # 获取列表的第一个元素（最新消息）
        message_json = self.redis_client.lindex(channel_key, 0)
        if not message_json:
            return None
            
        return json.loads(message_json)

    def _query_earliest(self, receiver: str) -> Optional[Dict[str, Any]]:
        """查询指定频道的最早消息（列表的最后一个元素）"""
        channel_key = f"ipc:channel:{receiver}"
        
        if not self.redis_client.exists(channel_key):
            return None
            
        # 获取列表的最后一个元素（最早消息）
        message_json = self.redis_client.lindex(channel_key, -1)
        if not message_json:
            return None
            
        return json.loads(message_json)

    def _fetch_earliest(self, receiver: str) -> Optional[Dict[str, Any]]:
        """获取并删除指定频道的最早消息"""
        channel_key = f"ipc:channel:{receiver}"
        
        if not self.redis_client.exists(channel_key):
            return None
            
        # 从右侧弹出（最早的消息）
        message_json = self.redis_client.rpop(channel_key)
        if not message_json:
            return None
            
        message = json.loads(message_json)
        self.logger(f"已获取并删除最早消息: {receiver} (ID: {message['id']})")
        return message

    def _process_requests(self):
        """处理客户端请求 - 使用BRPOP替代Streams"""
        self.logger("开始处理消息请求...")
        
        requests_list = "ipc:requests"
        
        while self.running:
            try:
                # 阻塞式获取请求（最多等待5秒）
                result = self.redis_client.brpop(requests_list, timeout=5)
                
                if not result:
                    continue
                
                # result格式: (list_name, request_json)
                _, request_json = result
                
                try:
                    request = json.loads(request_json)
                    response = self._handle_request(request)
                    
                    # 发送响应
                    if "client_id" in request and "request_id" in request:
                        response_key = f"ipc:response:{request['client_id']}:{request['request_id']}"
                        self.redis_client.setex(response_key, 30, json.dumps(response))
                        
                except Exception as e:
                    logging.error(f"处理请求时出错: {e}")
                    continue
                    
            except Exception as e:
                if self.running:
                    logging.error(f"请求处理循环出错: {e}")
                time.sleep(1)

    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理客户端请求"""
        action = request.get("action")
        receiver = request.get("receiver", "")
        sender = request.get("sender", "")
        content = request.get("content", "")
        
        if self.show:
            self.logger(f"服务端收到请求: {request}\n处理请求: {action} -> {receiver}")
        
        if action == "post":
            message = self._store_message(sender, receiver, content)
            return {
                "status": "success",
                "message_id": message["id"]
            }
        
        elif action == "query_latest":
            message = self._query_latest(receiver)
            if message:
                return {
                    "status": "success",
                    "count": 1,
                    "messages": [message]
                }
            else:
                return {
                    "status": "success",
                    "count": 0,
                    "messages": []
                }
        
        elif action == "query_earliest":
            message = self._query_earliest(receiver)
            if message:
                return {
                    "status": "success",
                    "count": 1,
                    "messages": [message]
                }
            else:
                return {
                    "status": "success",
                    "count": 0,
                    "messages": []
                }
        
        elif action == "fetch_earliest":
            message = self._fetch_earliest(receiver)
            if message:
                return {
                    "status": "success",
                    "count": 1,
                    "messages": [message]
                }
            else:
                return {
                    "status": "success",
                    "count": 0,
                    "messages": []
                }
        
        else:
            return {
                "status": "error",
                "message": f"未知操作: {action}"
            }

    def stop(self):
        """停止服务"""
        self.running = False


class BulletinClient:
    def __init__(self, client_name: str, host='localhost', port=6379, db=0, listen=False, show=False):
        self.client_name = client_name
        self.client_id = f"{client_name}_{int(time.time())}"
        self.show = show
        self.running = True
        
        # Redis 连接
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        
        # 测试连接
        try:
            self.redis_client.ping()
        except redis.ConnectionError:
            logging.error("无法连接到Redis服务器")
            raise
        
        self.message_callbacks = []
        
        if listen:
            self.thread = threading.Thread(target=self._listen_notifications, daemon=True)
            self.thread.start()

    def logger(self, message):
        if self.show: 
            logging.info(f"RedisIPCClient({self.client_name}): {message}")

    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求并等待响应"""
        request_id = str(uuid.uuid4())
        request["client_id"] = self.client_id
        request["request_id"] = request_id
        
        request_json = json.dumps(request)
        response_key = f"ipc:response:{self.client_id}:{request_id}"
        
        # 发送请求到列表
        self.redis_client.lpush("ipc:requests", request_json)
        
        # 等待响应
        start_time = time.time()
        
        while time.time() - start_time < 30:  # 30秒超时
            response_json = self.redis_client.get(response_key)
            if response_json:
                self.redis_client.delete(response_key)
                return json.loads(response_json)
            time.sleep(0.1)
        
        return {
            "status": "error",
            "message": "请求超时"
        }

    def _listen_notifications(self):
        """监听通知消息"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("ipc:notifications")
        
        self.logger("开始监听通知...")
        
        for message in pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    if data["event"] == "new_message":
                        message_obj = data["message"]
                        # 检查是否发送给当前客户端或是广播消息
                        if (message_obj["receiver"].lower() == "all" or 
                            message_obj["receiver"] == self.client_name):
                            for callback in self.message_callbacks:
                                callback(message_obj)
                except Exception as e:
                    logging.warning(f"处理通知时出错: {e}")

    def register_callback(self, callback: Callable):
        """注册消息回调"""
        self.message_callbacks.append(callback)

    def post_message(self, receiver: str, content: str, sender: str = None):
        """发布消息"""
        if sender is None:
            sender = self.client_name
            
        return self._send_request({
            "action": "post",
            "sender": sender,
            "receiver": receiver,
            "content": content
        })

    def query_latest_message(self, receiver: str):
        """查询指定频道的最新消息"""
        return self._send_request({
            "action": "query_latest",
            "receiver": receiver
        })

    def query_earliest(self, receiver: str):
        """查询指定频道的最早消息"""
        return self._send_request({
            "action": "query_earliest",
            "receiver": receiver
        })

    def fetch_earliest_messages(self, receiver: str):
        """获取并删除指定频道的最早消息"""
        return self._send_request({
            "action": "fetch_earliest",
            "receiver": receiver
        })

    def close(self):
        """关闭客户端"""
        self.running = False


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 启动服务端
    server = RedisIPCServer(show=True)
    
    # 客户端1
    client1 = BulletinClient("client1", listen=True, show=True)
    
    # 客户端2  
    client2 = BulletinClient("client2", listen=True, show=True)
    
    def print_message(message):
        print(f"收到消息: {message['sender']} -> {message['receiver']}: {message['content']}")
    
    client2.register_callback(print_message)
    
    # 测试
    print("测试开始...")
    
    # 发送消息
    result = client1.post_message("client2", "1")
    result = client1.post_message("client2", "2")
    result = client1.post_message("client3", "3")
    time.sleep(1)
    
    # 查询最新消息
    result = client2.query_latest("client2")
    print("最新消息:", result)
    
    # 查询最早消息
    result = client2.query_earliest("client2")  
    print("最早消息:", result)
    
    # 获取并删除最早消息
    result = client2.fetch_earliest("client2")
    print("获取最早消息:", result)
    
    # 再次查询确认删除
    result = client2.query_earliest("client2")
    print("删除后最早消息:", result)
    
    # 测试广播
    client1.post_message("all", "Broadcast message!")
    time.sleep(1)
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在关闭...")
        server.stop()
        client1.close()
        client2.close()