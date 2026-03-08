import socketio
import time

sio = socketio.Client()

@sio.event
def connect():
    print("CONNECTED TO WS")

@sio.on('market_update')
def market(data):
    print("MARKET EVENT:", data.get("symbol"), data.get("price"))

@sio.on('prediction_update')
def pred(data):
    print("PREDICTION EVENT:", data.get("symbol"), data.get("signal"))

sio.connect("http://127.0.0.1:5000")
print("Listening 30 seconds...")
time.sleep(30)
sio.disconnect()
