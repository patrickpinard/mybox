
#!/usr/bin/env python
# coding: utf-8
# Auteur    : Patrick Pinard
# Date      : 22.10.2021
# Objet     : Pilotage modules relais avec interface web basée sur API RESTful Flask et bootstrap sur PI zero 
# Version   :   2.1 - ajout du Thermostat pour contrôler le chauffage
#               2.0 - ajout d'un Framework Bootstrap pour un affichage plus pro
#               1.3 - ajout de la lecture de température via un thread
#               1.2 - modification du log file
#               1.1 - ajout du bouton shutdown externe
#               1.0 - version initiale fonctionelle
#  {} = "alt/option" + "(" ou ")"
#  [] = "alt/option" + "5" ou "6"
#   ~  = "alt/option" + n    
#   \  = Alt + Maj + / 

import RPi.GPIO as GPIO
from flask import Flask, Markup, render_template, request, redirect, jsonify, url_for, session, abort
from flask_restful import Resource, Api, reqparse
import logging
import datetime
from time import sleep
import os
from ds18b20 import DS18B20
from threading import Thread

PASSWORD    = 'password'
USERNAME    = 'admin'

t = 0       # température de la sonde DS18B20
Tmin = 0    # température minimale pour enclenchement du thermostat du chauffage
Tmax = 20   # température maximale pour déclenchement du thermostat du chauffage
Thermostat = False  # valeur True ou False pour déclenchement du chauffage
sensor = DS18B20()

legend = 'Sonde DS18B20'
temperatures = []
times = []

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
    global t, labels, values, legend, temperatures, times, Tmin, Tmax, Thermostat

    message = "logging"
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
                # Along with the pin dictionary, put the message into the template data dictionary:
                templateData = {
                    'message': message,
                    'pins': pins,
                    'temp' : t, 
                    'legend' : legend, 
                    'labels' : times, 
                    'values' : temperatures,
                    'Tmin' : Tmin,
                    'Tmax' : Tmax,
                    'Thermostat' : Thermostat
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
    global templateData,t,legend, temperatures, times, Tmin, Tmax, Thermostat

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
                    'temp' : t, 
                    'legend' : legend, 
                    'labels' : times, 
                    'values' : temperatures,
                    'Tmin' : Tmin,
                    'Tmax' : Tmax,
                    'Thermostat' : Thermostat
                }

    return render_template('main.html', **templateData)


@app.route("/set_thermostat", methods=["GET",'POST'])
def set_thermostat():
    global legend, temperatures, times, t, times, Tmin, Tmax, Thermostat
   
    message = "set thermostat values"

    if request.method == 'POST':
        Tmin=int(request.form['Tmin'])
        Tmax=int(request.form['Tmax'])

    text = "Thermostat values changed to Tmin : " + str(Tmin) + "  and Tmax :   (°Celsius)" + str(Tmax)
    logging.info(text)
    read_temp()
    templateData = {
                    'message': message,
                    'pins': pins,
                    'temp' : t, 
                    'legend' : legend, 
                    'labels' : times, 
                    'values' : temperatures,
                    'Tmin' : Tmin,
                    'Tmax' : Tmax,
                    'Thermostat' : Thermostat
                }

    return render_template('main.html', **templateData) 


@app.route("/refresh", methods=["GET",'POST'])
def refresh():
    global legend, temperatures, times, t, times, Tmin, Tmax, Thermostat
   
    message = "reading temp.."

    read_temp()
    templateData = {
                    'message': message,
                    'pins': pins,
                    'temp' : t, 
                    'legend' : legend, 
                    'labels' : times, 
                    'values' : temperatures,
                    'Tmin' : Tmin,
                    'Tmax' : Tmax,
                    'Thermostat' : Thermostat
                }

    return render_template('main.html', **templateData) 

def read_temp():

    global t, times, temperatures, Thermostat, sensor

    allTemp = sensor.get_temperatures([DS18B20.DEGREES_C, DS18B20.DEGREES_F, DS18B20.KELVIN])
    t = allTemp[0]
    temperatures.append(t)
    now = datetime.datetime.now()
    times.append(datetime.time(now.hour, now.minute, now.second))
    text = ("measure temperature, t : " + str(t) + " - time : " + str(datetime.time(now.hour, now.minute, now.second)))
    logging.info(text)
    if t < Tmin : 
        logging.info("Temperature is below Temp thermostat min. Starting radiator")
        Thermostat = False
    if t > Tmax : 
        logging.info("Temperature is upper Temp thermostat max. Stoping radiator")
        Thermostat = True

def loop():
    # Lecture de la température toute les 60 secondes  
    while True: 
        read_temp()
        sleep(60)

if __name__ == "__main__":
    app.secret_key = os.urandom(12)

    logging.info("###################################")
    logging.info("########   Relaybox V2.1  #########")
    logging.info("########   Patrick Pinard #########")
    logging.info("###################################")
    logging.info("program starting...")


    # Demarre le threadpour lecture température
    t1 = Thread(target=loop)
    t1.start()
    
    app.run(host='0.0.0.0', port=8001, debug=True)
