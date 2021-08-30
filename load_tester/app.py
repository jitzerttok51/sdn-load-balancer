from flask import Flask
import os

app = Flask(__name__)

counter = 0
host = os.environ['HOST']

@app.route("/")
def home():
    global counter
    counter = counter + 1
    save(host, counter)
    return f"{host}: {counter}" 

def save(host, count):
    with open(f"{host}.txt", 'w') as f:
        f.write(str(count))
