import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.progressbar import ProgressBar
from kivy.properties import ObjectProperty
from kivy.properties import NumericProperty
from kivy.clock import Clock, mainthread
from kivy.garden import knob
#from kivy.garden import gauge
from functools import partial
import paho.mqtt.client as mqtt



class MyGrid(GridLayout):
    temp = ObjectProperty(None)
    hum = ObjectProperty(None)
    lbl1 = ObjectProperty(None)
    lbl2 = ObjectProperty(None)
    knob1 = ObjectProperty(None)
    knob2 = ObjectProperty(None)

    @mainthread
    def update(self, temp, humid,*a):
        self.temp.value=float(temp)
        self.hum.value=float(humid)
        self.lbl2.text='T: ' + str(temp) + u'\N{DEGREE SIGN}' +'C'    
        self.lbl1.text='H: ' +str(humid) + ' %'
        self.knob2.value=float(humid)
        self.knob1.value=float(temp)

class mainApp(App):
    client = mqtt.Client("P1")
    def on_message(self,client, userdata, message):
        data=message.payload.decode("utf-8").split(':')

        self.root.update(data[0],data[1],1)

    def build(self):
        #client = mqtt.Client("P1") 
        self.client.on_message=self.on_message 
        self.client.connect('192.168.100.19',1883)
        self.client.loop_start()
        self.client.subscribe([("temp_mon/temp",0),("temp_mon/hum",0)])

        return MyGrid()

    def on_pause(self):
        self.client.disconnect()

    def on_resume(self):
        self.client.on_message=self.on_message 
        self.client.connect('192.168.100.19',1883)
        self.client.loop_start()
        self.client.subscribe([("temp_mon/temp",0),("temp_mon/hum",0)])


if __name__ == "__main__":
    mainApp().run()