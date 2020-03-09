import serial
import paho.mqtt.client as MqttClient
import configparser
import logging
import os
import sys
import queue
import threading
import time
import pybase64 
from signal import signal, SIGINT
# initial commit on github @ 09 03 2020
# connector prototype

logger = logging.getLogger('SerialToMQTT')
logfile_h = logging.FileHandler('log/SerialToMQTT.log')
format_h = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logfile_h.setFormatter(format_h)
logger.addHandler(logfile_h)
logger.setLevel(logging.INFO)

config = configparser.ConfigParser()
logger.info('Starting SerialToMQTT injector')

if (os.path.exists('config/SerialToMQTT.ini')):
    logger.info('Reading configuration file')
    config.read('config/SerialToMQTT.ini')
else:
    logger.error('Error reading configuration file. Please make sure that the file exists')
    logger.error('Application will exit')
    sys.exit(0)
    
try:
    logger.info('Reading configuration keys')
    conn_type=config['GENERAL']['conn_type']

    mqtt_ip=config['GENERAL']['mqtt_ip']
    mqtt_port=config['GENERAL']['mqtt_port']

    serial_port=config['GENERAL']['serial_port']
    serial_baud=config['GENERAL']['serial_baud']
    serial_parity=config['GENERAL']['serial_parity']
    serial_stop=config['GENERAL']['serial_stop']
    serial_bytesize=config['GENERAL']['serial_bytesize']

    device_id=config['DEVICE']['dev_id']

    logger.info('Config keys are VALID')
except:
    logger.error('Error reading config keys - invalid section found')

Rx_Queue=queue.Queue(maxsize=200)
Tx_Queue=queue.Queue(maxsize=200)
IPC_Queue=queue.Queue(maxsize=10)

logger.info('Connector type is: ' + conn_type)
logger.info('Trying to open the serial port')
try:
    Serial_Com = serial.Serial(serial_port, serial_baud, parity=serial_parity, stopbits=int(serial_stop), bytesize=int(serial_bytesize), timeout=1)
    logger.info('Serial port opened succesfuly')
    logger.info(Serial_Com)
except Exception as error:
    logger.info('Error opening serial port dumping error and application will exit')
    logger.error(error)
    sys.exit(0)

def handle_sigint(signal_received, frame):
    logger.info('Received CTRL+C or SIGINT')
    logger.info('Closing serial port')
    Serial_Com.close()
    logger.info('Application will now terminate')
    sys.exit(0)

def tx_send(ComPort):
    logger.info('Starting TX thread with ID: ' + str(tx_thread.ident))
    mqtt_tx=MqttClient.Client('mqtt_tx')
    try:
        logger.info('Trying to connect to MQTT broker @ ' + mqtt_ip + ':' + mqtt_port)
        mqtt_tx.connect(mqtt_ip, int(mqtt_port))
        logger.info('Connected to MQTT broker @ ' + mqtt_ip + ':' + mqtt_port)
    except Exception as e:
        logger.error(e)
        logger.error('TX thread now will exit and application will terminate from the main thread')
        IPC_Queue.put('E:' + str(tx_thread.ident) + ':10')
    while True:
        payload = ComPort.readline().strip().decode('utf-8')
        if payload=='':
            pass
        else:
            mqtt_tx.publish('device/' + device_id, pybase64.standard_b64encode(payload.encode('utf-8')))
            logger.info('Wrote payload to MQTT broker - payload is: ' + str(pybase64.standard_b64encode(payload.encode('utf-8'))))
        time.sleep(0.2)

def rx_get(ComPort):
    logger.info('Starting RX thread with ID: ' + str(rx_thread.ident))
    while True:
        time.sleep(1)
        #do nothing here at the moment

tx_thread = threading.Thread(target=tx_send, args=(Serial_Com,))  # start the thread for getting the payload from COM conn
tx_thread.daemon = True

rx_thread = threading.Thread(target=rx_get, args=(Serial_Com,))  # start the thread for getting the payload from COM conn
rx_thread.daemon = True

if __name__=='__main__':
    logger.info('Main thread started - proceding to start the worker threads')
    signal(SIGINT, handle_sigint)
    tx_thread.start()
    rx_thread.start()
    while True:
        if IPC_Queue.qsize()>0:
            IPC_content = IPC_Queue.get()
            if IPC_content[0]=='E':
                logger.error('Error received from worker ' + IPC_content +' - application will now stop')
                sys.exit(0)
        time.sleep(1)