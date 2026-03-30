from logging.handlers import RotatingFileHandler
import threading
import time
import VolitionLib.VolitionTree as VolitionTree
import RobotState
import IPC, lib_helper, datetime, os, logging, sys

settings = lib_helper.load_json_with_comments("settings.json")
if settings["do_log"]:
    log_dir = settings["log_dir"]
    log_dir = os.path.normpath(log_dir)
    now = datetime.datetime.now()
    now = now.strftime("%Y%m%d%H%M%S")
    path = os.path.join(log_dir, f"log_{now}.txt")
    handler = RotatingFileHandler(
        filename=path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,               # 保留 5 个备份文件
        encoding='utf-8'
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
                    handler,
                    logging.StreamHandler(sys.stdout)   # 同时输出到控制台（可选）
                ]
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# Test

IPCServer = IPC.BulletinBoardServer(False)
RS = RobotState.RobotState()
VT = VolitionTree.VolitionTree("让我感到开心一些", 0.7)
threading.Thread(target=RS.run, daemon=True).start()
threading.Thread(target=VT.run, daemon=True).start()
while True: 
    cmd = input().strip()
    if cmd == "quit":
        VT.quit()
        break