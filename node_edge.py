import sys, getopt
from flask import Flask, request
import time
import threading
import requests
import json
import random

FIND_SERVER_URL = "127.0.0.1:5000"
LOCAL_ADDR = "127.0.0.1"
LOCAL_SERVER_PORT = 5001
NODE_TYPE = "edge"
NODE_TYPES = ["cloud","edge","mobile"]
MAX_CONNECTION = 2
MAX_HOPS = 5
VERSION = 2020110701

Lock = threading.Lock()
raw_nodes = {}
connecing_nodes = {}
all_nodes = {
    "cloud":[],
    "edge":[],
    "mobile":[]
}
nodes_in_use = {
    "cloud":[],
    "edge":[]
}
inbox = []
block_chain = []
data_cache = []

app = Flask(__name__)

@app.route('/')
def hello_world():
    global a
    return 'Hello, World!'+str(a)

@app.route('/nodes')
def get_raw_nodes():
    global connecing_nodes
    return json.dumps(connecing_nodes)

@app.route('/ping',methods=["GET"])
def ping():
    global NODE_TYPE
    global VERSION
    global NODE_TYPES
    global LOCAL_ADDR
    global LOCAL_SERVER_PORT
    global connecing_nodes
    global Lock

    addr = request.remote_addr
    port = request.args.get("port")
    ntype = request.args.get("type")
    if addr=="127.0.0.1" and port==None and ntype=="interface":
        pass
    elif port!=None and ntype in NODE_TYPES:
        node = {
            "addr":addr,
            "port":port,
            "type":ntype,
            "time":int(time.time())
        }
        Lock.acquire()
        connecing_nodes[str(addr+":"+port)] = node
        Lock.release()
    else:
        abort(400)
        return
    data = {
        "ip":LOCAL_ADDR,
        "port":LOCAL_SERVER_PORT,
        "version":VERSION,
        "type":NODE_TYPE
    }
    return json.dumps(data)

@app.route("/blocks")
def get_blocks():
    global block_chain
    return json.dumps(block_chain)

#Local Request Only
@app.route("/data",methods=["POST"])
def get_data():
    global Lock
    global data_cache
    if request.remote_addr != "127.0.0.1":
        return "local request only"
    data = {
        "payload":request.get_json(),
        "hops":0
    }
    print(data)
    #Verify Data Here
    #----------------
    Lock.acquire()
    data_cache.append(data)
    Lock.release()
    return "ok"

@app.route("/data_detour",methods=["POST"])
def data_detour():
    global Lock
    global data_cache
    data = request.get_json()
    data["hops"] += 1
    print(data)
    Lock.acquire()
    data_cache.append(data)
    Lock.release()
    return "ok"

@app.route("/msg",methods=["POST"])
def receive_msg():
    global Lock
    global inbox

    in_msg = request.get_json()

    Lock.acquire()
    inbox.append(in_msg)
    Lock.release()
    return "received"

#Local Request Only
@app.route("/get_msg",methods=["GET"])
def get_msg():
    global inbox
    global Lock
    if request.remote_addr != "127.0.0.1":
        return "local request only"
    Lock.acquire()
    inbox_text = json.dumps(inbox)
    inbox = []
    Lock.release()
    return inbox_text

#Local Request Only
@app.route("/send_msg",methods=["POST"])
def send_msg():
    global LOCAL_ADDR
    global LOCAL_SERVER_PORT
    if request.remote_addr != "127.0.0.1":
        return "local request only"
    data = request.get_json()
    msg = {
        "from_ip":LOCAL_ADDR,
        "from_port":LOCAL_SERVER_PORT,
        "time":int(time.time()),
        "format":data["format"],
        "payload":data["payload"]
    }
    try:
        res = requests.post("http://{}:{}/msg".format(data["to_ip"],data["to_port"]),timeout=5,json=data)
        return "ok"
    except:
        print("Msg Send Err.")
        return "err"

#Only for Dev
@app.route("/observe",methods=["GET"])
def observe_page():
    global VERSION
    global FIND_SERVER_URL
    global NODE_TYPE
    global NODE_TYPES
    global LOCAL_ADDR
    global LOCAL_SERVER_PORT
    global connecing_nodes
    global nodes_in_use
    global block_chain
    global data_cache
    global inbox
    all_status = ""
    #all_status += "<meta http-equiv=\"refresh\" content=\"20\">\n"
    all_status += "<h1>Blockchain Env</h1>"
    all_status += "Version:{}<br>".format(VERSION)
    all_status += "{} @ {}:{}<br>".format(NODE_TYPE,LOCAL_ADDR,LOCAL_SERVER_PORT)
    all_status += "Find Server:{}<br>".format(FIND_SERVER_URL)

    all_status += "<h3>Network</h3>"
    all_status += "Connecting: Nodes:<br>{}<br>".format(str(connecing_nodes))
    all_status += "In Use Nodes:<br>{}<br>".format(str(nodes_in_use))

    all_status += "<h3>Data</h3>"
    all_status += "Blockchian:<br>{}<br>".format(str(block_chain))
    all_status += "Data Cache:<br>{}<br>".format(str(data_cache))
    all_status += "Message Inbox:<br>{}<br>".format(str(inbox))
    return all_status


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
        upload_data()
        if a % 20 == 0:
            print("**{}@{}:{}**".format(NODE_TYPE,LOCAL_ADDR,str(LOCAL_SERVER_PORT)))
            print("refresh nodes...")
            find_nodes()
            refresh_inuse_nodes()
            refresh_hops()
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
    #TODO:
    try:
        res = requests.get("http://{}?port={}&type={}".format(FIND_SERVER_URL,str(LOCAL_SERVER_PORT),NODE_TYPE))
    except:
        print("Cannot connect to Find Server")
        return
    raw_list = json.loads(res.text)
    raw_nodes = raw_list
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
        res = requests.get("http://{}:{}/ping?port={}&type={}".format(addr,port,str(LOCAL_SERVER_PORT),NODE_TYPE),timeout=5)
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
            if len(new_block_chain) > len(block_chain):
                block_chain = new_block_chain
        elif nodes_in_use["edge"]:
            node = random.choice(nodes_in_use["edge"])
            res = requests.get("http://{}:{}/blocks".format(node["addr"],node["port"]),timeout=5)
            new_block_chain = json.loads(res.text)
            if len(new_block_chain) > len(block_chain):
                block_chain = new_block_chain
        else:
            print("Refresh Nodes...")
            find_nodes()
            refresh_inuse_nodes()
            return False
        return True
    except:
        print("Refresh in-use Nodes...")
        refresh_inuse_nodes()
        return False

def upload_data():
    global Lock
    global data_cache
    global raw_nodes
    global all_nodes
    global nodes_in_use

    Lock.acquire()
    try:
        if nodes_in_use["cloud"]:
            for i in range(len(data_cache)-1,-1,-1):
                if data_cache[i]["hops"] > MAX_HOPS:
                    print("Max Hops, Ignore.")
                else:
                    node = random.choice(nodes_in_use["cloud"])
                    res = requests.post("http://{}:{}/data".format(node["addr"],node["port"]),timeout=5,json=data_cache[i])
                    if res.text == "ok":
                        print("Upload OK.")
                        del data_cache[i]
                    else:
                        print("Upload Err.")

        elif nodes_in_use["edge"]:
            for i in range(len(data_cache)-1,-1,-1):
                if data_cache[i]["hops"] > MAX_HOPS:
                    print("Max Hops, Ignore.")
                else:
                    node = random.choice(nodes_in_use["edge"])
                    res = requests.post("http://{}:{}/data_detour".format(node["addr"],node["port"]),timeout=5,json=data_cache[i])
                    if res.text == "ok":
                        print("Data Detour OK.")
                        del data_cache[i]
                    else:
                        print("Data Detour Err.")
        else:
            print("No Avaliable Node.")
        Lock.release()
        return True
    except:
        Lock.release()
        print("Conn Err...")
        return False

def refresh_hops():
    global Lock
    global data_cache
    print("Refresh Hops.")
    Lock.acquire()
    for data in data_cache:
        data["hops"] = 0 if data["hops"] > MAX_HOPS else data["hops"]
    Lock.release()

def opening():
    opening_str = """
\033[1;32;40m    ______         __     __          _     
   / ____/__  ____/ /____/ /_  ____ _(_)___ 
  / /_  / _ \\/ __  / ___/ __ \\/ __ `/ / __ \\
 / __/ /  __/ /_/ / /__/ / / / /_/ / / / / /
/_/    \\___/\\__,_/\\___/_/ /_/\\__,_/_/_/ /_/ 

Blockchain-based Federated Learning Platform \033[0m                        
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