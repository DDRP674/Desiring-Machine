from logging.handlers import RotatingFileHandler
from VolitionLib.VolitionTree import CastratedVolitionTree
import webbrowser
import datetime, os, logging, sys
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

file_path = os.path.abspath("./VolitionLib/Visualize/index.html")
webbrowser.open(file_path)
VT = CastratedVolitionTree(True)

def Quit():
    VT.quit()

while True: 
    try:
        cmd = input().strip()
        if cmd == "quit": Quit()
    except KeyboardInterrupt: Quit()