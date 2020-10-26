import requests
import json

VERSION = 2020102601

def check_node(port,n_type):
    global VERSION
    try:
        res = requests.get("http://localhost:{}/ping".format(port))
        res_json = json.loads(res.text)
        if res_json["type"] == n_type and res_json["version"] == VERSION:
            print("[BlockChain] Node OK")
            return True
        else:
            print("[BlockChain] Node Type/Version Error")
            return False
    except:
        print("[BlockChain] Node Error")
        return False

class Cloud():
    def __init__(self,port):
        self.port = port
        check_node(self.port,"cloud")

    # 获取当前节点中收到的数据
    def get_data(self):
        try:
            res = requests.get("http://localhost:{}/get_data".format(self.port))
            data = json.loads(res.text)
            return data
        except:
            print("[BlockChain] Unknown Error")
            return False

    # 向当前节点的区块链添加区块
    def add_block(self,block):
        try:
            res = requests.post("http://localhost:{}/addblock".format(self.port),json=block)
            if res.text == "ok":
                return True
            else:
                print("[BlockChain] Node Error")
                return False
        except:
            print("[BlockChain] Unknown Error")
            return False

    # 获取当前节点的区块链
    def get_blocks(self):
        try:
            res = requests.get("http://localhost:{}/blocks".format(self.port))
            blocks = json.loads(res.text)
            return blocks
        except:
            print("[BlockChain] Unknown Error")
            return False

class Edge():
    def __init__(self,port):
        self.port = port
        check_node(self.port,"edge")

    # 向当前节点添加上传数据
    def upload_data(self,data):
        try:
            res = requests.post("http://localhost:{}/data".format(self.port),json=data)
            if res.text == "ok":
                return True
            else:
                print("[BlockChain] Node Error")
                return False
        except:
            print("[BlockChain] Unknown Error")
            return False


    # 获取当前节点区块链 
    def get_blocks(self):
        try:
            res = requests.get("http://localhost:{}/blocks".format(self.port))
            blocks = json.loads(res.text)
            return blocks
        except:
            print("[BlockChain] Unknown Error")
            return False



