from flask import Flask, request
import os
import threading
import time
import socket

app = Flask(__name__)

counter = 0
host = os.environ['HOST']
monitorIp = os.environ['MONITOR_IP']
monitorPort = int(os.environ['MONITOR_PORT'])

load = {}
timeouts = {}

@app.route("/")
def home():
    count()
    return f"{host}: {counter}" 

@app.route("/load")
@app.route("/load/<magnitude>")
@app.route('/load/<magnitude>/<seconds>')
def addLoad(magnitude="1", seconds="1"):
    global load
    count()
    reqId = request.__hash__()
    load[reqId] = int(magnitude)
    timeouts[reqId] = time.time() + int(seconds)
    return magnitude

def count():
    global counter
    counter = counter + 1
    save(host, counter)

def save(host, count):
    with open(f"{host}.txt", 'w') as f:
        f.write(str(count))


def cleanTimeouts():
    global timeouts
    global load
    expired = [req for req, t in timeouts.items() if t <= time.time()]
    for e in expired:
        del timeouts[e]
        del load[e]

def submitLoad():
    cleanTimeouts()
    hostLoad = sum(load.values())
    print(f"Current load: {hostLoad}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(hostLoad.to_bytes(4, byteorder='big'), (monitorIp, monitorPort))

def createTimer(target, seconds):
    def iter():
        while True:
            target()
            time.sleep(seconds)
    th = threading.Thread(target=iter, daemon=True)
    th.start()
    return th

if __name__ == "__main__":
    createTimer(submitLoad, 2)
    app.run(host="0.0.0.0", debug=False)