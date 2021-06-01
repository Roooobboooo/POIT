from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect  
import MySQLdb
import time
import random
import math
import serial
import matplotlib.pyplot as plt
import numpy as np
import configparser as ConfigParser

async_mode = None

app = Flask(__name__)

config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print (myhost)

ser=serial.Serial('/dev/ttyS1',9600)
ser.baudrate=9600

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 


def background_thread(args):
    count = 0    
    dataCounter = 0 
    dataList = []  
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
    fo = open("static/files/skuska.txt","a+")
    fo.write('[')
    while True:
        if args:
          A = dict(args).get('A')
          btnV = dict(args).get('btn_value')
          dbV = dict(args).get('db_value')
        else:
          A = 0
          btnV = 'null'
          sliderV = 0
          dbV = 'nieco'
        print (args)
        socketio.sleep(0.05)
        read_ser=ser.readline()
        y=[]
        if read_ser != b'OK':
            y.append(float(read_ser))
            prem = y[-1]
            print(prem)
            read_ser=ser.readline()
            count += 1
            dataCounter +=0.01
            prem = y
            if len(dataList)>0:
              print (str(dataList))
              print (str(dataList).replace("'", "\""))
            socketio.emit('my_response',
                          {'data': prem[-1], 'count': count},
                          namespace='/test')  
        if dbV == 'start':
          fo = open("static/files/skuska.txt","a+")
          dataDict = {
            "t": time.time(),
            "x": dataCounter,
            "y": prem[-1]}
          fo.write("y=" +str(dataCounter)+ ", x=" +str(prem[-1]))
          dataList.append(dataDict) 
        else:
          fo.close
          if len(dataList)>0:
            print (str(dataList))
            fuj = str(dataList).replace("'", "\"")
            print (fuj)
            cursor = db.cursor()
            cursor.execute("SELECT MAX(id) FROM graph")
            maxid = cursor.fetchone()
            cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (maxid[0] + 1, fuj))
            db.commit()
          dataList = []
          dataCounter = 0 
    db.close()
@app.route('/')
def index():
    return render_template('index_povodny.html', async_mode=socketio.async_mode)
       
@app.route('/graphlive', methods=['GET', 'POST'])
def graphlive():
    return render_template('graphlive.html', async_mode=socketio.async_mode)

@app.route('/gauge', methods=['GET', 'POST'])
def gauge():
    return render_template('gauge.html', async_mode=socketio.async_mode)
   

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html', async_mode=socketio.async_mode)
    
@app.route('/db')
def db():
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute('''SELECT  hodnoty FROM  graph''')
  rv = cursor.fetchall()
  return str(rv)    

@app.route('/dbdata/<string:num>', methods=['GET', 'POST'])
def dbdata(num):
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  print (num)
  cursor.execute("SELECT hodnoty FROM  graph WHERE id=%s", num)
  rv = cursor.fetchone()
  return str(rv[0])

@app.route('/write')
def write2file():
    fo = open("static/files/skuska.txt","a+")
    val = "a"
    fo.write("%s\r\n" %val)
    return "done"

@app.route('/read/<string:num>')
def readmyfile(num):
    fo = open("static/files/skuska.txt","r")
    rows = fo.readlines()
    return rows[int(num)-1]

@app.route('/graph2', methods=['GET', 'POST'])
def graph2():
    return render_template('graph2.html', async_mode=socketio.async_mode)
    
    
@socketio.on('db_event', namespace='/test')
def db_message(message):   
    session['db_value'] = message['value']    


@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['A'] = message['value']    
    
 
@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())


@socketio.on('click_event', namespace='/test')
def db_message(message):   
    session['btn_value'] = message['value']    


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)