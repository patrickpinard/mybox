
#!/usr/bin/env python
# coding: utf-8
# Auteur    : Patrick Pinard
# Date      : 22.10.2021
# Objet     : Pilotage modules relais avec interface web basée sur API RESTful Flask et bootstrap sur PI zero 
# Version   :   2.0 - ajout d'un Framework Bootstrap pour un affichage plus pro
#               1.3 - ajout de la lecture de température via un thread
#               1.2 - modification du log file
#               1.1 - ajout du bouton shutdown externe
#               1.0 - version initiale fonctionelle

import RPi.GPIO as GPIO
from flask import Flask, render_template, request, redirect, jsonify, url_for, session, abort
from flask_restful import Resource, Api, reqparse
import logging
import time
import os
from ds18b20 import DS18B20
from threading import Thread

PASSWORD    = 'password'
USERNAME    = 'admin'
t = 0       # température de la sonde DS18B20


logging.basicConfig(filename='mybox.log', filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


app = Flask(__name__, static_url_path='', static_folder='static')
app = Flask(__name__)


# Create a dictionary called pins to store the pin number, name, and pin state:
pins = {
    17: {'name': 'Relai 1', 'state': GPIO.LOW, 'status': "OFF"},  #GPIO.LOW
    27: {'name': 'Relai 2', 'state': GPIO.LOW, 'status': "OFF"},
    22: {'name': 'Relai 3', 'state': GPIO.LOW, 'status': "OFF"},
    20: {'name': 'Relai 4', 'state': GPIO.LOW, 'status': "OFF"}
}

# Set each pin as an output and make it low:
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

@app.route('/', methods=["GET", "POST"])
def login():

    if request.method == "GET":
        # Check if user already logged in

        if not session.get("logged_in"):
            logging.info("login not done, redirect to 'login' page")
            name = request.form.get("username")
            pwd = request.form.get("password")
            logging.info("user: " + str(name) + " password : " + str(pwd) + "try to login")
            return render_template('login.html', error_message=" welcome ! ")
        else:
            logging.info("login already done, redirect to 'main' page")
            return render_template('main.html')

    if request.method == "POST":
        # Try to login user

        name = request.form.get("username")
        pwd = request.form.get("password")

        if pwd == PASSWORD and name == USERNAME:
                logging.info("user: " + name + " logged in")
                session['logged_in'] = True
                # For each pin, read the pin state and store it in the pins dictionary:
                for pin in pins:
                    pins[pin]['state'] = GPIO.input(pin)
                # Put the pin dictionary into the template data dictionary:
                templateData = {
                    'pins': pins
                }
                # Pass the template data into the template main.html and return it to the user
                return render_template('main.html', **templateData)
        else:
                logging.warning(" !!!!  login with wrong username and password  !!!")
                logging.info("user: " + str(name) + " with password : " + str(pwd) + " try to login without success")
                return render_template('login.html', error_message="wrong username and password. Please try again")

@app.route("/logout", methods=["GET",'POST'])
def logout():
    session["logged_in"] = False
    logging.info("user logout")
    return render_template('login.html')           


@app.route("/cmd", methods=['POST'])
def cmd():
    global templateData,t

    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('pin', type=str, required=True)           
    args = parser.parse_args()
    pin = int(args['pin'])

    GPIO.output(pin, not GPIO.input(pin))

    if pins[pin]['status'] == "ON":
        pins[pin]['status'] = "OFF"   
        message = "PIN# " + str(pin) + " changed to state : OFF"
    else:
        pins[pin]['status'] = "ON"
        message = "PIN# " + str(pin) + " changed to state : ON"
    
    logging.info(message)
    pins[pin]['state'] = GPIO.input(pin)

    # Along with the pin dictionary, put the message into the template data dictionary:
    templateData = {
        'message': message,
        'pins': pins,
        'temp' : t
    }
    return render_template('main.html', **templateData)

def read_temp():
    # Lecture de la température toute les dix secondes et mise à jour de la variable t 
    global t
    sensor = DS18B20()
    while True: 
        allTemp = sensor.get_temperatures([DS18B20.DEGREES_C, DS18B20.DEGREES_F, DS18B20.KELVIN])
        t = allTemp[0]
        time.sleep(10)
        
@app.route("/refresh", methods=["GET",'POST'])
def refresh():
    global templateData
    global t
    
    message = "refresh temperature measure"
    templateData = {
        'message': message,
        'pins': pins,
        'temp' : t
    }
    logging.info(message)
    return render_template('main.html', **templateData) 

if __name__ == "__main__":
    app.secret_key = os.urandom(12)

    logging.info("###################################")
    logging.info("########   Relaybox V2.0  #########")
    logging.info("########   Patrick Pinard #########")
    logging.info("###################################")
    logging.info("program starting...")


    # Demarre le threadpour lecture température
    t1 = Thread(target=read_temp)
    t1.start()
    
    app.run(host='0.0.0.0', port=8001, debug=True)
