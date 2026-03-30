import logging
import time
import threading
from flask import Flask, jsonify
from flask_cors import CORS

class API: # 待测试
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        
        self.lock = threading.Lock()
        self.TreeData = {"id": "Root", "value": 0.0, "children": []}
        self.CurrentID = "Root"
        self.log = logging.getLogger('werkzeug')
        self.log.setLevel(logging.WARNING)

        # 设置路由
        @self.app.route('/api/tree-data', methods=['GET'])
        def get_tree_data():
            return jsonify({
                "treeData": self.TreeData,
                "stateData": {
                    "CurrentNodeID": self.CurrentID,
                    "TriggerState": False
                }
            })
        
        # 在后台线程中启动Flask应用
        threading.Thread(target=self._run_flask, daemon=True).start()

    def _run_flask(self):
        """在单独线程中运行Flask应用"""
        self.app.run(port=5000, debug=False, use_reloader=False)

    def Update(self, treedata, currentid):
        if self.TreeData != treedata: self.TreeData = treedata
        if self.CurrentID != currentid: self.CurrentID = currentid

    def test(self):
        import testingdata
        time.sleep(3)
        self.Update(testingdata.TESTDATA_1, "Root")
        time.sleep(3)
        self.Update(testingdata.TESTDATA_1, "7a4737d9-987d-4330-ad25-f9aa1cdb4878")
        time.sleep(3)
        self.Update(testingdata.TESTDATA_2, "7a4737d9-987d-4330-ad25-f9aa1cdb4878")

# 使用示例
if __name__ == '__main__':
    test = API()
    
    # 保持主线程运行
    try:
        while True:
            test.test()
    except KeyboardInterrupt:
        print("程序退出")