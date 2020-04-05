import sys
import time
import RPi.GPIO as GPIO
import dht11
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QAction, QMessageBox
from PyQt5 import QtWidgets, uic, QtCore
from configparser import ConfigParser
from pathlib import Path

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

config_file='config.ini'
config_parse = ConfigParser()

if Path(config_file).is_file():
    config_parse.read('config.ini')
else:
    sys.exit(1)

class GetTemp(QtCore.QThread):
    str_temp= QtCore.pyqtSignal(str)
    str_hum= QtCore.pyqtSignal(str)
    label_css=QtCore.pyqtSignal(str)

    temp_alarm_css=QtCore.pyqtSignal(str)
    hum_alarm_css=QtCore.pyqtSignal(str)

    instance = dht11.DHT11(pin = 17)

    def __init__(self,  parent=None): #init class - as far as i know is not mandatory ... but ok
        QtCore.QThread.__init__(self, parent)
        self.running = False

    def run(self):   #define a method that would emit a str signal from time to time (3 sec apart)
        self.running = True
        while self.running:
            result = self.instance.read()
            if result.is_valid():
                self.label_css.emit('background: green; border-radius: 20px;')

                if int(result.temperature) < int(config_parse.get('TEMPMON','temp_low')):
                    self.temp_alarm_css.emit('background: red; border-radius: 20px;')
                else:
                    self.temp_alarm_css.emit('background: green; border-radius: 20px;')

                if int(result.humidity) < int(config_parse.get('TEMPMON','hum_low')):
                    self.hum_alarm_css.emit('background: red; border-radius: 20px;')
                else:
                    self.hum_alarm_css.emit('background: green; border-radius: 20px;')

                self.str_temp.emit(str(result.temperature))
                self.str_hum.emit(str(result.humidity))

            else:
                self.label_css.emit('background: red; border-radius: 20px;')
            time.sleep(5)

    def stop(self):
        self.label_css.emit('background: yellow; border-radius: 20px;')
        self.running=False


class Window(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        uic.loadUi('main.ui', self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.move(0,0)
        self.btn_exit.clicked.connect(self.ExitApp)
        self.stop_a.clicked.connect(self.StopAq)
        self.start_a.clicked.connect(self.StartAq)

        self.GetTempThread=GetTemp()
        self.GetTempThread.str_temp.connect(self.temp.display)
        self.GetTempThread.str_hum.connect(self.hum.display)
        self.GetTempThread.temp_alarm_css.connect(self.temp.setStyleSheet)
        self.GetTempThread.hum_alarm_css.connect(self.hum.setStyleSheet)
        self.GetTempThread.label_css.connect(self.l_temp.setStyleSheet)
        self.GetTempThread.label_css.connect(self.l_hum.setStyleSheet)
        self.GetTempThread.start()

        self.show()

    def ExitApp(self):
        sys.exit(0)

    def StopAq(self):
        self.GetTempThread.stop()

    def StartAq(self):
        self.GetTempThread.start()

app = QtWidgets.QApplication(sys.argv)
window = Window()
app.exec_()