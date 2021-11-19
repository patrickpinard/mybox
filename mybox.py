
#!/usr/bin/env python
# coding: utf-8
# Auteur    : Patrick Pinard
# Date      : 13.11.2021
# Objet     : Pilotage modules relais avec interface web basée sur API RESTful Flask et bootstrap sur PI zero 
# Version   :   3.2 - optimisation code et requete http/get lors changement d'état d'un des switches checkbox toggle
#               3.1 - ajout du checkbox toggle sur relais
#               3.0 - réorganisation des données dans des dictionnaires et ajout de pages html distinctes pour graphiques et tables 
#               2.0 - ajout d'un Framework Bootstrap pour un affichage plus pro
#               1.3 - ajout de la lecture de température via un thread
#               1.2 - modification du log file
#               1.1 - ajout du bouton shutdown externe
#               1.0 - version initiale fonctionelle

#   Clavier MAC :      
#  {} = "alt/option" + "(" ou ")"
#  [] = "alt/option" + "5" ou "6"
#   ~  = "alt/option" + n    
#   \  = Alt + Maj + / 



import RPi.GPIO as GPIO
from flask import Flask, Markup, render_template, request, redirect, jsonify, url_for, session, abort
from flask_restful import Resource, Api, reqparse
import logging
import datetime
import pickle
from time import sleep, strftime
import os
from ds18b20 import DS18B20
from threading import Thread


# anciennes variables : 
sensor = DS18B20()
now = datetime.datetime.now()
t = now.strftime("%d/%m/%Y, %H:%M:%S")
legend = ''

times = []
chauffage = []
outside_temp = []
inhouse_temp = []
sensors = []
Tin = 0
Tout = 0
temp = 0            # température de la sonde DS18B20
Tmin = 5            # température minimale pour enclenchement du thermostat du chauffage
Tmax = 10           # température maximale pour déclenchement du thermostat du chauffage
Thermostat = True   # valeur True ou False pour déclenchement du chauffage sur relai 3
MAXSIZE = 100
INTERVAL_TIME_MESURE = 900
DEBUG = True

pins = {
        17: {'name': 'Relai 1', 'state': GPIO.HIGH, 'status': "OFF"},  
        27: {'name': 'Relai 2', 'state': GPIO.HIGH, 'status': "OFF"},
        22: {'name': 'Relai 3', 'state': GPIO.HIGH, 'status': "OFF"},
        23: {'name': 'Relai 4', 'state': GPIO.HIGH, 'status': "OFF"}
    }


# Création UTILISATEUR / MOT DE PASSE: 
PASSWORD    = 'password'
USERNAME    = 'admin'
FILENAME    = "data.bin"

# Création du FICHIER LOG: 
logging.basicConfig(filename='/home/pi/mybox/mybox.log', filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Définition des pins GPIO:
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# Création de l'APPLICATION FLASK:
app = Flask(__name__, static_url_path='', static_folder='static')
app = Flask(__name__)

# Définition des pins en output et mise à zero (circuit ouvert = gpio.high; circuit fermé = gpio.low):
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

def LoadTemplateData():
    global legend, labels, values, inhouse_temp, outside_temp, times, temp, t, times, Tmin, Tmax, Thermostat, chauffage, Tin, Tout, pins
    return      {
                    'message': "message",
                    'pins': pins,
                    'temp' : temp, 
                    'legend' : legend, 
                    'labels' : times, 
                    'Tin' : Tin,
                    'Tout' : Tout,
                    'inhouse_temp' : inhouse_temp,
                    'outside_temp' : outside_temp,
                    'Tmin' : Tmin,
                    'Tmax' : Tmax,
                    'Thermostat' : Thermostat,
                    't' : t,
                    'relay3': chauffage
                }

def SaveData():
    global times, chauffage, outside_temp, inhouse_temp
    try: 
        with open(FILENAME, 'wb') as file:
            pickle.dump(times, file)
            pickle.dump(chauffage, file)
            pickle.dump(outside_temp, file)
            pickle.dump(inhouse_temp, file)
            if DEBUG : print("données sauvegardées dans le fichier : ", FILENAME )
    except : 
        if DEBUG : print("erreur de sauvegarde des données. Impossible d'écrire sur fichier : ", FILENAME)

def LoadData():
    global times, chauffage, outside_temp, inhouse_temp

    try: # Open NVM file if it exists otherwise use defaults
        with open(FILENAME, 'rb') as file:
            times  = pickle.load(file)
            chauffage  = pickle.load(file)
            outside_temp      = pickle.load(file)
            inhouse_temp = pickle.load(file)
            if DEBUG : 
                print("times         : ", times)
                print("thermostat    : ", chauffage)
                print("temp. externe : ", outside_temp)
                print("temp. interne : ", inhouse_temp)
    except:
        if DEBUG : print("erreur dans le chargement des données depuis fichier : ", FILENAME)

@app.route('/', methods=["GET", "POST"])
def login():
    global legend, labels, values, inhouse_temp, outside_temp, times, temp, t, times, Tmin, Tmax, Thermostat, chauffage, pins

    message = "logging"
    legend = "temp"
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
                templateData = LoadTemplateData()
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

@app.route("/table", methods=["GET",'POST'])
def table():
    templateData = LoadTemplateData()
    return render_template('table.html',**templateData)    

@app.route("/graph", methods=["GET",'POST'])
def graph():
    read_temp()
    templateData = LoadTemplateData()
    return render_template('graph.html',**templateData )  

@app.route("/set_thermostat", methods=["GET",'POST'])
def set_thermostat():

    global Tmin, Tmax, Thermostat
   
    Tmin = int(request.form.get("Tmin"))
    
    Tmax = int(request.form.get("Tmax"))
    checkbox = request.form.get('Thermostat')
   
    if checkbox :
        Thermostat = True
        logging.info("Thermostat activé")
    else:
        Thermostat = False
        logging.info("Thermostat désactivé")

    text = "Thermostat avec T. min = " + str(Tmin) + " Tmax = " + str(Tmax)
    logging.info(text)
    read_temp()
    templateData = LoadTemplateData()

    return render_template('main.html', **templateData) 

@app.route("/togglerelay", methods=["GET",'POST'])
def togglerelay():
    global Thermostat

    pin = int(request.args.get('id'))
    checked = request.args.get('checked')
    
    if pin == 22:
        if not Thermostat:
            if checked=="true":
                pins[pin]['status'] = "ON"
            elif checked=="false":
                pins[pin]['status'] = "OFF"
            else:
                print("Erreur")
            
            GPIO.output(pin, not GPIO.input(pin))
            pins[pin]['state'] = GPIO.input(pin)
            text = "pin #id : " + str(pin) + " change d'état à : " + pins[pin]['status']

        else:
            text = "Thermostat enclenché. Pas de changement possible"
    
    else:       
        if pins[pin]['status'] == "ON":
            pins[pin]['status'] = "OFF"   
        else:
            pins[pin]['status'] = "ON"
        
        GPIO.output(pin, not GPIO.input(pin))
        pins[pin]['state'] = GPIO.input(pin)
        text = "pin #id : " + str(pin) + " change d'état à : " + pins[pin]['status']

    read_temp()
    templateData = LoadTemplateData()
    logging.info(text)

    return render_template('main.html', **templateData) 

@app.route("/refresh", methods=["GET",'POST'])
def dashboard():
    global t
    now = datetime.datetime.now()
    t = now.strftime("%H:%M:%S")
    read_temp()
    templateData = LoadTemplateData()
    SaveData()
    LoadData()
    return render_template('main.html', **templateData) 

def read_temp():

    global t, times, Tmin, Tmax, Thermostat, chauffage, Tin, Tout, MAXSIZE

    # lecture des senseurs de températures et ajout dans la liste des mesures
    for sensor_id in DS18B20.get_available_sensors():
        sensors.append(DS18B20(sensor_id))
    
    Tout =round(sensors[0].get_temperature(DS18B20.DEGREES_C),2)
    Tin= round(sensors[1].get_temperature(DS18B20.DEGREES_C),2)
    
    outside_temp.append(round(sensors[0].get_temperature(DS18B20.DEGREES_C),2))
    inhouse_temp.append(round(sensors[1].get_temperature(DS18B20.DEGREES_C),2))
    
    # lecture de l'heure et ajout dans la liste du temps
    now = datetime.datetime.now()
    t = now.strftime("%-d/%-m %H:%M")  
    times.append(t)  
    
    # si le dictionnaire contient plus de MAXSIZE valeurs, on supprime la première (plus ancienne) de façon à garder un graphique affichable 
    
    if len(times) > MAXSIZE:
        times.pop(0)
        outside_temp.pop(0)
        inhouse_temp.pop(0)
        logging.info("Suppression de l'élement le plus ancien de la liste des mesures")   

    if Thermostat: 
        if Tin < Tmin : 
            logging.info("Température intérieure est plus basse que la valeur thermostat minimale. Chauffage enclenché (relai n°3)")
            GPIO.output(22,0)
            
        if Tin >= Tmax : 
            logging.info("Température intérieure est plus haute que la valeur thermostat maximale. Chauffage stoppé (relai n°3)")
            GPIO.output(22,1)

        pins[22]['state'] = GPIO.input(22)
    
    if pins[22]['state']:
        chauffage.append(0)
    else:
        chauffage.append(10)
    

def loop():
    # Lecture de la température toute les INTERVAL_TIME_MESURE (sec))  
    global  INTERVAL_TIME_MESURE

    while True: 
        read_temp()
        sleep(INTERVAL_TIME_MESURE)



if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    logging.info("#######        MyBox       #########")
    logging.info("#######   V3.2 du 13.11.2021  #########")
    logging.info("#######   Patrick Pinard   #########")

    # Demarre le threadpour lecture température
    t1 = Thread(target=loop)
    t1.start()
    
    app.run(host='0.0.0.0', port=80, debug=False)
