import logging
import subprocess
import threading
import time, testingdata
import API, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import lib_helper, IPC

do_display = True
Cooldown = 0.5
running = True
activated = True
lock = threading.Lock()

process = subprocess.Popen(
        "redis-server",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
IPCServer = IPC.RedisIPCServer(show=False)

def g(cooldown=1):
    ipc = IPC.BulletinClient("test")
    while True:
        ipc.post_message(ipc.client_name, "1", ipc.client_name)
        ipc.query_latest_message(ipc.client_name)
        ipc.fetch_earliest_messages(ipc.client_name)
        time.sleep(cooldown)

def f(cooldown=1):
    if not do_display: return
    try: JSAPI = API.API()
    except Exception as e:
        logging.warning(f"未启动前端：{e}")
        return
    while running:
        JSAPI.test()

threading.Thread(target=f, daemon=True).start()
threading.Thread(target=g, daemon=True).start()
while True: input()