import time
import network
import uasyncio as asyncio
from BLE_CEEO import Yell
from mqtt import MQTTClient
from machine import ADC, Pin

from Conductor import Conductor # Class to control the tune
from secrets import mysecret, key

# ------ CREATING AND CONNECTING MIDI CONDUCTOR ------
midi = Yell('Anne', verbose = True, type = 'midi')
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
topic_sub = 'ME35-24/Conduct' 
topic_pub = 'ME35-24/Team'
chorusDone = False

async def callback(topic, msg):
    global conductor
    global chorusDone
    
    val = msg.decode()
    print("MQTT Message received: "+val)
    
    # Listening for start/stop commands from light sensor
    if val == 'done':
        chorusDone = True
        print("------- CALLBACK - CHORUS DONE!!! ----------")
    elif val == 'begin_music':
        conductor.startSong()
        print("Got begin music message in music box")
        print("CALLBACK - PLAY SONG")
    
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

def sendMQTT(client, msg):
    print("in sendMQTT")
    try:
        client.publish(topic_pub.encode(), msg.encode())
        print("Sent message: "+msg)
    except Exception as e:
        client.connect()
        print("Reconnected, trying again...")
        client.publish(topic_pub.encode(), msg.encode())
        
async def conductClass(client, conductor):
    global chorusDone
    
    onMessages = ["on_1", "on_2", "on_3", "on_4", "on_5", "on_6"]
    offMessages = ["off_1", "off_2", "off_3", "off_4", "off_5", "off_6"]
    
    print("-------- STARTING -----------")
    
    for i in range(0, 6): # 6 pairs
        print("Now in pair number "+ str(i))
        sendMQTT(client, onMessages[i])
        sendMQTT(client, "begin_music")
        conductor.startSong()
        
        print("-------- Pair "+str(i)+" of 5 ---------")
        
        while not chorusDone:
            #print("Chorus in progress")
            await asyncio.sleep(0.1)
        
        sendMQTT(client, offMessages[i])
        sendMQTT(client, offMessages[i]) # sending twice for redundancy
        chorusDone = False
        
    print("------- Song over! ------")
    

# ----- RUNNING ASYNC FUNCTIONS -----
conductor.turnOn()
loop = asyncio.get_event_loop()
loop.create_task(mqtt_handler(client))
loop.create_task(conductClass(client, conductor))
loop.create_task(conductor.playSong())
loop.run_forever()

