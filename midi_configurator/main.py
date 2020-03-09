import sys
import queue
import serial
import time
import threading
import os
import psutil

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from configparser import ConfigParser
from datetime import datetime
from resources import uiresource
from PyQt5.QtCore import QTimer

config=ConfigParser()
config.read(os.path.abspath(os.path.dirname(sys.argv[0]))+'/config.ini')

Tx_Queue=queue.Queue(maxsize=200)
Rx_Queue=queue.Queue(maxsize=200)
Log_Queue=queue.Queue(maxsize=200)
Bck_Queue=queue.Queue(maxsize=200)

class UpdateThread(QtCore.QThread):
    str_signal=QtCore.pyqtSignal(str) #declare the custom signal

    def __init__(self,  parent=None): #init class - as far as i know is not mandatory ... but ok
        QtCore.QThread.__init__(self, parent)
        self.running = False

    def run(self):   #define a method that would emit a str signal from time to time (3 sec apart)
        self.running = True
        self.str_signal.emit('<font color=green><b>[INFO]</b></font>GUI update thread id: ' + str(int(QtCore.QThread.currentThreadId())))
        while self.running:
            time.sleep(0.2)
            self.str_signal.emit(str(Log_Queue.get()))

    def stop(self):
        self.str_signal.emit('Background thread will be terminated after its outstanding work will be done')
        self.running=False

class Ui(QtWidgets.QMainWindow):

    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(os.path.abspath(os.path.dirname(sys.argv[0]))+'/ui/main.ui', self)
        
        for midi_idx in range(1,17):
            self.MIDICHNL.addItem(str(midi_idx))
        self.MIDICHNL.addItem('OMNI')

        for midi_idx in range(1,128):
            self.MIDICC.addItem(str(midi_idx))
        for midi_idx in range(1,9):
            self.OUTPUTNO.addItem(str(midi_idx))
        
        self.actionE_xit.triggered.connect(app.quit)
        self.action_Write_board_config.triggered.connect(self.UploadBoardConfig)
        self.action_Save.triggered.connect(self.SaveBoardConfig)
        self.action_About.triggered.connect(self.ShowAboutDialog)

        self.WMIDICNL.clicked.connect(self.write_midi_cnl)
        self.WOUTSET.clicked.connect(self.write_output_settings)

        self.GetLog = UpdateThread()
        self.GetLog.str_signal.connect(self.WLOG.append)
        self.GetLog.start()
  
        Log_Queue.put('<font color=green><b>[INFO]</b></font>Utility running at: ' + str(os.path.abspath(os.path.dirname(sys.argv[0]))))
        
        try:
            Serial_Com = serial.Serial(config.get('GENERAL', 'com_port'), 9600, timeout=1)
            self.statusBar().setStyleSheet('QStatusBar{padding-left:8px;background:green;color:white;font-weight:bold;}')
            self.statusBar().showMessage('Connected to - ' + config.get('GENERAL', 'com_port') + '/ 9600')
            Log_Queue.put('<font color=green><b>[INFO]</b></font>Serial port is: ' + str(Serial_Com.name) + ' @ ' + str(Serial_Com.baudrate))
        except:
            self.statusBar().setStyleSheet('QStatusBar{padding-left:8px;background:red;color:white;font-weight:bold;}')
            msgBox = QMessageBox()
            msgBox.critical(self, 'Error opening ' + config.get('GENERAL', 'com_port'),'Please make sure that ' + config.get('GENERAL', 'com_port') +' port is avialable and working' + '\r\n' + 'Application will now exit!')
            sys.exit(0)

        tx_thread = threading.Thread(target=self.tx_send, args=(Serial_Com,))  # start the thread for getting the payload from COM conn
        tx_thread.daemon = True
        tx_thread.start()

        rx_thread = threading.Thread(target=self.rx_get, args=(Serial_Com,))  # start the thread for getting the payload from COM conn
        rx_thread.daemon = True
        rx_thread.start()

        bk_thread = threading.Thread(target=self.bk_make, args=())
        bk_thread.daemon=True
        bk_thread.start()

        Log_Queue.put('<font color=green><b>[INFO]</b></font>TTL TX thread running with thread ID: ' + str(tx_thread.ident))
        Log_Queue.put('<font color=green><b>[INFO]</b></font>TTL RX thread running with thread ID: ' + str(rx_thread.ident))
        Log_Queue.put('<font color=green><b>[INFO]</b></font>Backup thread running with thread ID: ' + str(bk_thread.ident))
        Log_Queue.put('<font color=green><b>[INFO]</b></font>Initial process memory is: ' + str(round(psutil.Process(os.getpid()).memory_info()[0]/1024/1024,2)) + ' MB')
        self.show()

    def ShowAboutDialog(self):
        msgBox = QMessageBox()
        msgBox.information(self, 'About DWS Configurator' ,'This application is distributed under ...')


    def UploadBoardConfig(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Send board configuration","","All Files (*);;Text Files (*.cfg)", options=options)
        if fileName:
            print(fileName)
            FileHandle=open(fileName,'r')
            for line in FileHandle:
                Tx_Queue.put(line)
            FileHandle.close()

    def bk_make(self):
        while True:
            if Bck_Queue.qsize()!=0:
                payload=Bck_Queue.get()
                if payload[0]=='F':
                    print(payload[2:])
                    try:
                        fileHandle=open(payload[2:])

                    except Exception as errorHandle:
                        Log_Queue.put('<font color=red><b>[ERROR]</b></font>Error opening backup file - ' + str(payload[2:]) + ' at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        Log_Queue.put('<font color=red><b>[ERROR]</b></font>Previous error was - ' + str(errorHandle) + ' at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        Log_Queue.put('<font color=green><b>[INFO]</b></font>Cleaning communication queue started at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        with Bck_Queue.mutex:
                            Bck_Queue.queue.clear()

                if  payload[0]=='W':
                    try:
                        Log_Queue.put('<font color=green><b>[INFO]</b></font>Backing up location - ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        fileHandle.write(payload+'\n')
                    except Exception as errorHandle:
                        Log_Queue.put('<font color=red><b>[ERROR]</b></font>Error writing backup file - ' + str(payload[2:]) + ' at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        Log_Queue.put('<font color=red><b>[ERROR]</b></font>Previous error was - ' + str(errorHandle) + ' at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        Log_Queue.put('<font color=green><b>[INFO]</b></font>Cleaning communication queue started at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        with Bck_Queue.mutex:
                            Bck_Queue.queue.clear()
                            
                if payload[0]=='D':
                    try:
                        Log_Queue.put('<font color=green><b>[INFO]</b></font>Closing file - ' + str(fileHandle.name) + ' at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        fileHandle.close()
                        Log_Queue.put('<font color=green><b>[INFO]</b></font>Finished board backup process - ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                    except Exception as errorHandle:
                        Log_Queue.put('<font color=red><b>[ERROR]</b></font>Error closing backup file - ' + str(payload[2:]) + ' at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        Log_Queue.put('<font color=red><b>[ERROR]</b></font>Previous error was - ' + str(errorHandle) + ' at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        Log_Queue.put('<font color=green><b>[INFO]</b></font>Cleaning communication queue started at ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
                        with Bck_Queue.mutex:
                            Bck_Queue.queue.clear()
            time.sleep(0.2)

    def SaveBoardConfig(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,"Save board configuration","","Cfg Files (*.cfg)", options=options)
        if fileName:
            Log_Queue.put('<font color=green><b>[INFO]</b></font>Starting board backup process - ' + str(datetime.now().strftime('%b %d %Y %H:%M:%S.%f')))
            #print(fileName)
            Bck_Queue.put('F:' + fileName)
            #Tx_Queue.put('S:0:0')


    def tx_send(self,ser):
        while True:
            if Tx_Queue.empty!=True:
                ser.write(Tx_Queue.get().encode())
            else:
                pass
            time.sleep(0.2)
    
    def rx_get(self, ser):
        while True:
            payload = ser.readline().strip().decode('utf-8')
            #print(payload)
            if payload=='':
                pass
            else:
                if payload[0]=='!':
                    Log_Queue.put('<font color=green><b>[INFO]</b></font>Operation succeded - ' + str(datetime.now().strftime("%b %d %Y %H:%M:%S")))
                else:
                    if payload[0]=='W' or payload[0]=='D':
                        print('Putting in Bkq')
                        Bck_Queue.put(payload)
                        #print(payload)
                    
            time.sleep(0.2)

    def write_midi_cnl(self):
        snd_cmd='W:0:' + str(self.MIDICHNL.currentIndex()+1)+'\r\n'
        Tx_Queue.put(snd_cmd)
        print(snd_cmd)

    def write_output_settings(self):
        snd_cmd='W:' + str(self.OUTPUTNO.currentIndex()+100) + ':' + str(self.MIDICC.currentIndex()+1)+'\r\n'
        Tx_Queue.put(snd_cmd)
        print (snd_cmd)

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()