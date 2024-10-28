import time
import network
import uasyncio as asyncio
from BLE_CEEO import Yell
from mqtt import MQTTClient
from machine import ADC, Pin

from Conductor import Conductor # Class to control the tune
from secrets import mysecret, key

# ------ CREATING AND CONNECTING MIDI CONDUCTOR ------
midi = Yell('frog', verbose = True, type = 'midi')
conductor = Conductor(midi)
conductor.connect()
conductor.createClient()

# ------ MQTT SET UP ------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(mysecret, key)
    while not wlan.isconnected():
        time.sleep(1)
    print('----- connected to wifi -----')
        
# ------ CONNECTING UP MQTT -------
mqtt_broker = 'broker.emqx.io'
port = 1883
topic_sub = 'ME35-24/Team' 
topic_pub = 'ME35-24/Team'
async def callback(topic, msg):
    global conductor
    
    val = msg.decode()
    print("MQTT Message received: "+val)
    
    # Listening for start/stop commands from light sensor
    if val == 'begin_music':
        await conductor.playSong()
        print("CALLBACK - PLAY SONG")
        
    elif val == 'stop':
        await conductor.turnMasterOff()
        print("CALLBACK - STOPPING")

    # Listening for MQTT from the accelerometer data
    elif val[0] == 'T':
        await conductor.changeTempo(float(val[1:]))
        print("CALLBACK - CHANGED TEMPO TO: "+str(val[1:]))

connect_wifi()
client = MQTTClient('AnnePico', mqtt_broker, port, keepalive=60)
client.set_callback(lambda topic, msg: asyncio.create_task(callback(topic,msg)))
client.connect()
client.subscribe(topic_sub.encode())
print(f'Subscribed to {topic_sub}')

# ---- HANLER FUNCTIONS------
def connect_mqtt(client):
    client.connect()
    client.subscribe(topic_sub.encode())
    print(f'Subscribed to {topic_sub}')
    
async def mqtt_handler(client):
    while True:
        if network.WLAN(network.STA_IF).isconnected():
            try:
                client.check_msg()
            except Exception as e:
                print('MQTT callback failed')
                connect_mqtt(client)
        else:
            print('Wifi disconnected, trying to connect...')
            connect_wifi()
        await asyncio.sleep(0.01)
    

# ----- RUNNING ASYNC FUNCTIONS -----
loop = asyncio.get_event_loop()
loop.create_task(mqtt_handler(client))
conductor.turnOn()
loop.create_task(conductor.playSong())
loop.run_forever()

