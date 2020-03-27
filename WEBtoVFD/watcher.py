import paho.mqtt.client as MsgSubscribe
import time
import queue
import threading
import smbus
import RPi.GPIO as GPIO

broker= 'localhost'
port = 1883
display_time= 20

i2c_bus = smbus.SMBus(1)
i2c_address = 0x20
strobe_pin= 4

GPIO.setmode(GPIO.BCM)
GPIO.setup(strobe_pin, GPIO.OUT)
GPIO.setwarnings(False)


ContentQ = queue.Queue(maxsize=400)

def ResetDisplay():
    i2c_bus.write_byte(i2c_address, 0x1F)
    GPIO.output(strobe_pin, 1)
    time.sleep(0.001)
    GPIO.output(strobe_pin, 0)

def DimmingDisplay(dimvalue):
    #dimming values 0x20 / 0x40 / 0x60 / 0xFF
    i2c_bus.write_byte(i2c_address, 0x04)
    GPIO.output(strobe_pin, 1)
    time.sleep(0.001)
    GPIO.output(strobe_pin, 0)
    i2c_bus.write_byte(i2c_address, dimvalue)
    GPIO.output(strobe_pin, 1)
    time.sleep(0.001)
    GPIO.output(strobe_pin, 0)

def CursorOFF():
    i2c_bus.write_byte(i2c_address, 0x14)
    GPIO.output(strobe_pin, 1)
    time.sleep(0.001)
    GPIO.output(strobe_pin, 0)

def WriteString(string):
    for char in string:
        i2c_bus.write_byte(0x20, ord(char))
        GPIO.output(4, 1)
        time.sleep(0.001)
        GPIO.output(4, 0)

def SetDisplay():
    ResetDisplay()
    DimmingDisplay(0x60)
    CursorOFF()

def rx_get():
    while True:
        if ContentQ.empty!=True:
            SetDisplay()
            WriteString(ContentQ.get())
        else:
            pass
        time.sleep(display_time)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("webmessage/content")

def on_message(client, userdata, msg):
    ContentQ.put(msg.payload.decode())

rx_thread = threading.Thread(target=rx_get, args=())  # start the thread for getting the payload from COM conn
rx_thread.daemon = True
rx_thread.start()

client = MsgSubscribe.Client()
client.connect(broker,port,60)

client.on_connect = on_connect
client.on_message = on_message

client.loop_forever()