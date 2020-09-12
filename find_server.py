from flask import Flask, request
from flask_apscheduler import APScheduler
import time
import json
import threading
import socket

LOCAL_PORT = 5000
OVERTIME_INTERVAL = 300
NODE_TYPES = ["cloud","edge","mobile"]
nodes = {}

app = Flask(__name__)

class SchedulerConfig(object):
    JOBS = [
        {
            'id': 'clean_overtime_nodes', # 任务id
            'func': '__main__:clean_overtime_nodes', # 任务执行程序
            'args': None, # 执行程序参数
            'trigger': 'interval', # 任务执行类型，定时器
            'seconds': 10, # 任务执行时间，单位秒
        }
    ]

def clean_overtime_nodes():
    global nodes
    now_time = int(time.time())
    remove_list = []
    for n in nodes:
        if now_time - nodes[n]["time"] > OVERTIME_INTERVAL:
            remove_list.append(n)
    print("rm nodes", remove_list)
    for rn in remove_list:
        del nodes[rn]

@app.route('/',methods=["GET"])
def get_nodes():
    global nodes
    addr = request.remote_addr
    port = request.args.get("port")
    ntype = request.args.get("type")
    if ntype not in NODE_TYPES:
        return "TYPE ERROR"
    node = {
        "addr":addr,
        "port":port,
        "type":ntype,
        "time":int(time.time())
    }
    nodes[str(addr+":"+port)] = node
    #print(nodes)
    return json.dumps(nodes)

@app.route('/ip',methods=["GET"])
def get_ip():
    return request.remote_addr


if __name__ == '__main__':
    addr = socket.gethostbyname(socket.gethostname())
    print("** Find Server run @ \033[1;32;40m{}:{}\033[0m **".format(addr,int(LOCAL_PORT)))
    app.config.from_object(SchedulerConfig())
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()
    app.run("0.0.0.0", LOCAL_PORT, False)
    #123
