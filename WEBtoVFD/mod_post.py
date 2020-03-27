from flask import Flask, render_template, request
import time
import paho.mqtt.client as mqtt_client

broker ='localhost'
port= 1883

pub_client=mqtt_client.Client('WebPub')

app=Flask(__name__)

@app.route('/send/', methods=['post', 'get'])
def send():
    pub_client.connect(broker, port)
    if request.method == 'POST':
        line_one = request.form.get('line_one')
        line_two = request.form.get('line_two')
        pub_client.publish('webmessage/content', line_one + ' ' + line_two )
        pub_client.disconnect()
    return render_template('send_form.html', message='Message was sent to Dexter\'s WorkShop')
