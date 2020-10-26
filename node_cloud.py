import sys, getopt
from flask import Flask, request
import time
import threading
import requests
import json
import random
import hashlib

FIND_SERVER_URL = "127.0.0.1:5000"
LOCAL_ADDR = "127.0.0.1"
LOCAL_SERVER_PORT = 5002
NODE_TYPE = "cloud"
NODE_TYPES = ["cloud","edge","mobile"]
MAX_CONNECTION = 2

Lock = threading.Lock()
raw_nodes = []
all_nodes = {
    "cloud":[],
    "edge":[],
    "mobile":[]
}
nodes_in_use = {
    "cloud":[],
    "edge":[]
}
block_chain = []
data_cache = []
inbox = {}

app = Flask(__name__)

@app.route('/')
def hello_world():
    global a
    return str(a)

@app.route('/nodes')
def get_raw_nodes():
    return json.dumps(raw_nodes)

@app.route('/ping')
def ping():
    return "pong"

@app.route('/type')
def node_type():
    global NODE_TYPE
    return NODE_TYPE

@app.route("/blocks")
def get_blocks():
    global block_chain
    return json.dumps(block_chain)

#Local Request Only 
@app.route("/addblock",methods=["POST"])
def add_blocks():
    global block_chain
    global Lock
    if request.remote_addr != "127.0.0.1":
        return "local request only"
    Lock.acquire()
    block_chain.append(request.get_json())
    Lock.release()
    return "ok"

@app.route("/data",methods=["POST"])
def get_data():
    global Lock
    global data_cache
    data = request.get_json()
    print(data)
    Lock.acquire()
    data_cache.append(data["payload"])
    Lock.release()
    return "ok"

#Local Request Only 
@app.route("/get_data",methods=["GET"])
def get_data_test():
    global Lock
    global data_cache
    if request.remote_addr != "127.0.0.1":
        return "local request only"
    Lock.acquire()
    data_text = json.dumps(data_cache)
    data_cache = []
    Lock.release()
    return data_text

@app.route("/msg",methods=["POST"])
def get_msg():
    global Lock
    global inbox

    in_msg = request.get_json()
    m = hashlib.md5(in_msg["from_ip"]+str(in_msg["from_port"])+str(in_msg["time"]).encode())
    msg_id = m.hexdigest()

    Lock.acquire()
    inbox[msg_id] = in_msg["payload"]
    Lock.release()
    
    return msg_id

def main_loop():
    global a
    global raw_nodes
    global all_nodes
    a = 0
    find_nodes()
    refresh_inuse_nodes()
    while True:
        a = a+1
        #print(a)
        get_blocks_from_nodes()
        if a % 20 == 0:
            print("**{}@{}:{}**".format(NODE_TYPE,LOCAL_ADDR,str(LOCAL_SERVER_PORT)))
            print("refresh nodes...")
            find_nodes()
            refresh_inuse_nodes()
        time.sleep(5)

def get_ip():
    global LOCAL_ADDR
    try:
        res = requests.get("http://{}/ip".format(FIND_SERVER_URL))
        LOCAL_ADDR = res.text
        return True
    except:
        return False

def find_nodes():
    global raw_nodes
    global all_nodes
    try:
        res = requests.get("http://{}?port={}&type={}".format(FIND_SERVER_URL,str(LOCAL_SERVER_PORT),NODE_TYPE))
    except:
        print("Cannot connect to Find Server")
        return
    raw_list = json.loads(res.text)
    raw_nodes = raw_list
    #print(raw_list)
    temp_nodes = {
        "cloud":[],
        "edge":[],
        "mobile":[]
    }
    for n in raw_list:
        if raw_list[n]["addr"] != LOCAL_ADDR or raw_list[n]["port"] != str(LOCAL_SERVER_PORT):
            temp_nodes[raw_list[n]["type"]].append({
                "addr":raw_list[n]["addr"],
                "port":raw_list[n]["port"]
                })
    all_nodes = temp_nodes
    print(temp_nodes)

def ping_node(addr,port):
    try:
        res = requests.get("http://{}:{}/ping".format(addr,port),timeout=5)
        if res.status_code == 200:
            return True
        else:
            return False
    except:
        return False

def refresh_inuse_nodes():
    global raw_nodes
    global all_nodes
    global nodes_in_use
    nodes_in_use = {
        "cloud":[],
        "edge":[]
    }
    random_order = list(range(len(all_nodes["cloud"])))
    #print(random_order)
    random.shuffle(random_order)
    #print(random_order)
    for i in random_order:
        if ping_node(all_nodes["cloud"][i]["addr"],all_nodes["cloud"][i]["port"]):
            nodes_in_use["cloud"].append(all_nodes["cloud"][i])
        if len(nodes_in_use["cloud"]) > MAX_CONNECTION:
            break
    random_order = list(range(len(all_nodes["edge"])))
    #print(random_order)
    random.shuffle(random_order)
    #print(random_order)
    for i in random_order:
        if ping_node(all_nodes["edge"][i]["addr"],all_nodes["edge"][i]["port"]):
            nodes_in_use["edge"].append(all_nodes["edge"][i])
        if len(nodes_in_use["edge"]) > MAX_CONNECTION:
            break
    print(nodes_in_use)

def get_blocks_from_nodes():
    global raw_nodes
    global all_nodes
    global nodes_in_use
    global block_chain

    try:
        if nodes_in_use["cloud"]:
            node = random.choice(nodes_in_use["cloud"])
            res = requests.get("http://{}:{}/blocks".format(node["addr"],node["port"]),timeout=5)
            new_block_chain = json.loads(res.text)
            ###################
            #TODO
            ###################
            if len(new_block_chain) > len(block_chain):
                block_chain = new_block_chain
        elif nodes_in_use["edge"]:
            node = random.choice(nodes_in_use["edge"])
            res = requests.get("http://{}:{}/blocks".format(node["addr"],node["port"]),timeout=5)
            new_block_chain = json.loads(res.text)
            ###################
            #TODO
            ###################
            if len(new_block_chain) > len(block_chain):
                block_chain = new_block_chain
        else:
            print("refresh nodes...")
            find_nodes()
            refresh_inuse_nodes()
            return False
        return True
    except:
        print("refresh in-use nodes...")
        refresh_inuse_nodes()
        return False

def direct_msg(to_ip,to_port,payload):
    global LOCAL_ADDR
    global LOCAL_SERVER_PORT

    data = {
        "from_ip":LOCAL_ADDR,
        "from_port":LOCAL_SERVER_PORT,
        "time":int(time.time()),
        "payload":payload
    }
    try:
        res = requests.post("http://{}:{}/msg".format(to_ip,to_port),timeout=5,json=data)
    except:
        print("Msg Send Err.")

def del_msg_inbox(msg_id):
    global Lock
    global inbox
    Lock.acquire()
    try:
        del inbox[msg_id]
    except:
        print("Del Err")
    Lock.release()
    return True

def opening():
    opening_str = """
    ____  __           __        __          _             ______          
   / __ )/ /___  _____/ /_______/ /_  ____ _(_)___        / ____/___ _   __
  / __  / / __ \\/ ___/ //_/ ___/ __ \\/ __ `/ / __ \\______/ __/ / __ \\ | / /
 / /_/ / / /_/ / /__/ ,< / /__/ / / / /_/ / / / / /_____/ /___/ / / / |/ / 
/_____/_/\\____/\\___/_/|_|\\___/_/ /_/\\__,_/_/_/ /_/     /_____/_/ /_/|___/  
                                                                           
    """
    print(opening_str)


if __name__ == '__main__':
    opening()
    try:
        argv = sys.argv[1:]
        opts, args = getopt.getopt(argv,"hf:p:")
    except getopt.GetoptError:
        print ('argv err')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('test.py -f [find_server_addr:port] -p [local_port]')
            sys.exit()
        elif opt in ("-f"):
            FIND_SERVER_URL = arg
        elif opt in ("-p"):
            LOCAL_SERVER_PORT = int(arg)
    while not get_ip():
        print("Retry...")
        time.sleep(2)
    print("FIND_SERVER_URL",FIND_SERVER_URL,"\nLOCAL_ADDR",LOCAL_ADDR,"\nLOCAL_SERVER_PORT",LOCAL_SERVER_PORT)
    web_server = threading.Thread(target=app.run,args=("0.0.0.0", LOCAL_SERVER_PORT, False))
    web_server.setDaemon(True)
    web_server.start()

    main_loop()