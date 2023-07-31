import time

from Adafruit_IO import MQTTClient

from mqtt_modules.Virtual_assistant import *

AIO_FEED_ID = ["Chatbot"]
AIO_USERNAME = ""
AIO_KEY = ""


def connected(client):
    print("Connected to server!!!")
    for things in AIO_FEED_ID:
        client.subscribe(things)


def subscribe(client, userdata, mid, granted_qos):
    print("Subscribe sucessfully ...")


def disconnected(client):
    print("Disconnected ...")
    sys.exit(1)


def message(client, feed_id, payload):
    print(f"AI result from {feed_id} : {payload}")


client = MQTTClient(AIO_USERNAME, AIO_KEY)
client.on_connect = connected
client.on_disconnect = disconnected
client.on_message = message
client.on_subscribe = subscribe
client.connect()
client.loop_background()

while True:
    ai = AI()
    client.publish("Chatbot", ai)
    time.sleep(30)