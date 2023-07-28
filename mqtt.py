import time
import sys
from Adafruit_io import MQTTClient
from datetime import date, datetime


AIO_FEED_ID = [" Today " ," Time " ]
AIO_USERNAME = " "
AIO_KEY = " "

def connected(client) :
    print(" Connected to server !!!")
    for feeds in AIO_FEED_ID:
        client.subscribe(feeds)

def subscribe(client,userdata , mid , granted_qos ) :
    print ("Subscribe sucessfully ... ")

def disconnected(client):
    print("Disconnected from server!")
    sys.exit (1)

def message(client, feed_id, payload):
    print("Receive data: " + payload)

client = MQTTClient(AIO_USERNAME , AIO_KEY)
client.on_connect = connected
client.on_disconnect = disconnected
client.on_message = message
client.on_subscribe = subscribe
client.connect()
client.loop_background()