from logging.handlers import RotatingFileHandler
import subprocess
import threading
import VolitionLib.VolitionTree as VolitionTree
import RobotState
import IPC, datetime, os, logging, sys
import UI.UI
import lib_helper

settings = lib_helper.load_json_with_comments("settings.json")
if settings["do_log"]:
    log_dir = settings["log_dir"]
    log_dir = os.path.normpath(log_dir)
    now = datetime.datetime.now()
    now = now.strftime("%Y%m%d%H%M%S")
    path = os.path.join(log_dir, f"log_{now}.txt")
    handler = RotatingFileHandler(
        filename=path,
        maxBytes=10 * 1024 * 1024, 
        backupCount=5, 
        encoding='utf-8'
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            handler,
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# run

process = subprocess.Popen(
        "redis-server", # You need Redis for this version. Sorry about that
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
IPCServer = IPC.RedisIPCServer(show=False)
RS = RobotState.RobotState()
VT = VolitionTree.VolitionTree("Make anyeone sit on the chair in front of you and company you", "testtree", 0.7)
threading.Thread(target=RS.run, daemon=True).start()
threading.Thread(target=VT.run, daemon=True).start()
threading.Thread(target=UI.UI.main, daemon=True).start()
while True: 
    cmd = input().strip()
    if cmd == "quit":
        VT.quit()
        process.terminate()
        try: process.wait(timeout=5)
        except: process.kill()
        break