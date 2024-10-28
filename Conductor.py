import time
import network
import uasyncio as asyncio
from BLE_CEEO import Yell
from mqtt import MQTTClient
from machine import Pin, PWM # not in use yet...
from secrets import mysecret, key

class Conductor():

    # Initializer takes midi object
    def __init__(self, midiBluetooth):
        self.midi = midiBluetooth
        
        self.masterOn = False
        self.isOn = False
        
        self.tempo = 1.5
        self.vol = 'f'
        
        self.client = None
        self.topic_pub = 'ME35-24/Team'
        
        print("----- conductor successfully instantiated------")
    
    # ------ MQTT SET UP ------
    def connect_wifi(self):
        from secrets import mysecret, key
        
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(mysecret, key)
        while not wlan.isconnected():
            time.sleep(1)
        print('----- Conductor object is connected to wifi -----')
        
    def createClient(self):
        self.connect_wifi()
        
        mqtt_broker = 'broker.hivemq.com'
        port = 1883

        self.client = MQTTClient('ConductorObject', mqtt_broker, port, keepalive=120)
        self.client.connect()
        print("Conductor object has created a client!!!")
    
    # ------- HELPER FUNCTIONS --------
    async def turnMasterOn(self):
        self.masterOn  = True
        await asyncio.sleep(0.01)
        print(" ~~~~~~ from conductor: masterOn() ~~~~~")
        
    async def turnMasterOff(self):
        self.masterOn = False
        await asyncio.sleep(0.01)
        print("~~~~~~ from conductor: masterOff() ~~~~~")
        
    def turnOn(self):
        self.isOn = True
        print(" ~~~~~~ from conductor: turnOn() ~~~~~")
        
    def turnOff(self):
        self.isOn = False
        print(" ~~~~~~ from conductor: turnOff() ~~~~~")
    
    async def changeTempo(self, val):
        self.tempo = float(val)
        print("-------- TEMPO CHANGED!!!!! -------")
        print(" ------- " + str(self.tempo)+ " ----------")
        await asyncio.sleep(0.01)
    
    def changeVol(self, val):
        #val must be input as one of the corresponding velocity options
        self.vol = val
        msg = None
        
        if val == 'f':
            msg = 'SN'
        elif val == 'ff':
            msg = 'LU'
        elif val == 'p':
            msg = 'LI'
            
        try:
            self.client.publish(self.topic_pub.encode(), msg.encode())
            print("Sent character message to Dahal Board")
        except Exception as e:
            self.client.connect()
            print("Reconnected, trying again...")
            self.client.publish(self.topic_pub.encode(), msg.encode())
            
    
    def getTempo(self):
        return self.tempo

    def connect(self):
        self.midi.connect_up()
        
    def disconect(self):
        self.midi.disconnect()
    
    def checkState(self):
        return self.isOn        
        
    async def playSong(self):
        # ----- MIDI SETUP ------
        velocity = {'off':0, 'pppp':8,'ppp':20,'pp':31,'p':42,'mp':53,
            'mf':64,'f':80,'ff':96,'fff':112,'ffff':127}
        
        channel = 0
        timestamp_ms = time.ticks_ms()
        tsM = (timestamp_ms >> 7 & 0b111111) | 0x80
        tsL =  0x80 | (timestamp_ms & 0b1111111)
        NoteOn = 0x90
        NoteOff = 0x80
       
        from halloweenSong import notes

        print("about to start playing!!!")
        # For each note in song, make sure light uncovered, then play
        for i in range(0, len(notes)):
            event = notes[i]
            
            msg_type = (event[0] == 'note_on')
            command = NoteOn if msg_type else NoteOff

            note = event[1]
            velocity = event[2]
            duration = event[3]
                        
            while not self.isOn:
                print(" ------- Waiting for go on note #: "+str(i)+" --------")
                await asyncio.sleep(0.01)
            
            # When isOn, will play the note
            payload = bytes([tsM,tsL, command | channel, note, velocity]) # need to update the timestamp
            self.midi.send(payload)    
            await asyncio.sleep(duration)

