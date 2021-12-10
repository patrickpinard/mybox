#!/usr/bin/env python
# coding: utf-8
"""
Auteur    : Patrick Pinard
Date      : 08.12.2021
Objet     : Pilotage modules 4 relais et 2 sondes températures (intérieure
            et extérieure) avec interface web basée sur Flask et
            bootstrap sur PI zero

Version   :   3.5 - ajout de l'eventlog
              3.4 - correctif affichage graph avec chauffage
              3.3 - simplification du template html pour être plus compatible
                    avec IOS
              3.2 - optimisation code et requete http/get lors changement
                    d'état d'un des switches checkbox toggle
              3.1 - ajout du checkbox toggle sur relais pour faire plus fun
              3.0 - réorganisation des données dans des dictionnaires
                    (pas encore JSON, mais peut être plus tard)
              2.0 - ajout d'un Framework Bootstrap pour un affichage plus pro
              1.3 - ajout de la lecture de température via un thread
              1.2 - modification du log file
              1.1 - ajout du bouton shutdown externe
              1.0 - version initiale fonctionelle

   Clavier MAC :
  {} = "alt/option" + "(" ou ")"
  [] = "alt/option" + "5" ou "6"
   ~  = "alt/option" + n
   \  = Alt + Maj + /

 """

import RPi.GPIO as GPIO
from flask import Flask, Markup, render_template, request
from flask import redirect, jsonify, url_for, session, abort
from flask_restful import Resource, Api, reqparse
import logging
import datetime
import pickle
from time import sleep, strftime
import os
from ds18b20 import DS18B20
from threading import Thread


# variables :

sensor = DS18B20()          # senseurs de températures (externe et interne)
times = []                  # liste des points de mesures dans le temps
chauffage = []              # liste des activité ON/OFF du chauffage
outside_temp = []           # liste des températures internes mesurées (inside)
inhouse_temp = []           # liste des températures externes mesurées (outside)
sensors = []                # liste des senseurs de températures de type DS18B20
Tin = 0                     # température interne (inside)
Tout = 0                    # température externe (outside)
Tmin = 5                    # température minimale pour enclenchement du thermostat du chauffage
Tmax = 10                   # température maximale pour déclenchement du thermostat du chauffage
Thermostat = True           # valeur True ou False pour déclenchement du chauffage sur relai 3
MAXSIZE = 100               # taille maximale de conservation des mesures et eventlog
INTERVAL_TIME_MESURE = 900  # intervalle de temps entre mesures températures
camera = False              # activation de la caméra (picamera.ppdlab.ch) pour visualiser l'atelier
event = {"id": "",
         "date": "",
         "time": "",
         "what": ""}         # un type d'eventlog affiché sur l'interface
eventlog = []               # liste des eventlog
n = 0                       # nombre d'evenlog enregistré

DIRECTORY = "/home/pi/mybox/"             # répertoire par défaut
FILENAME = DIRECTORY + "myboxdata.bin"   # fichier de sauvegarde et restauration des données
LOGFILE = DIRECTORY + "mybox.log"       # fichier de log

# ensemble des relais avec nom, pin GPIO et état initial OFF
pins = {
        17: {'name': 'Relai 1', 'state': GPIO.HIGH, 'status': "OFF"},
        27: {'name': 'Relai 2', 'state': GPIO.HIGH, 'status': "OFF"},
        22: {'name': 'Relai 3', 'state': GPIO.HIGH, 'status': "OFF"},
        23: {'name': 'Relai 4', 'state': GPIO.HIGH, 'status': "OFF"}
    }


# Création du FICHIER LOG:
logging.basicConfig(filename=LOGFILE,
                    filemode='w',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Définition des pins GPIO sur Raspberry pi zero:
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# Création de l'APPLICATION FLASK:
app = Flask(__name__)

# Définition des pins en output et mise à zero
# (circuit ouvert = gpio.high; circuit fermé = gpio.low):
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)


def LogEvent(message):

    # Log des événements dans une table et dans fichier log

    global eventlog, event, MAXSIZE, n

    now = datetime.datetime.now()
    d = now.strftime("%d/%m/%Y")
    t = now.strftime("%H:%M")
    n = n+1
    id = n
    event = {"id": id, "date": d, "time": t, "what": message}
    eventlog.insert(0, event)

    l = len(eventlog)
    if l > MAXSIZE-1:
        eventlog.pop(l-1)
    logging.info(message)
    return


def LoadTemplateData():
    # chargement de l'ensemble des données dans
    # un template transmis au front-end bootstrap

    global inhouse_temp, outside_temp, times, Tmin, Tmax, Thermostat, chauffage, Tin, Tout, pins, camera, eventlog
    return {
             'pins': pins,
             'labels': times,
             'Tin': Tin,
             'Tout': Tout,
             'inhouse_temp': inhouse_temp,
             'outside_temp': outside_temp,
             'Tmin': Tmin,
             'Tmax': Tmax,
             'Thermostat': Thermostat,
             'chauffage': chauffage,
             'camera': camera,
             'eventlog': eventlog
            }


def SaveData():

    # Sauvegarde des données enregistrées sur disque

    global times, chauffage, outside_temp, inhouse_temp, eventlog
    try:
        with open(FILENAME, 'wb') as file:
            pickle.dump(times, file)
            pickle.dump(chauffage, file)
            pickle.dump(outside_temp, file)
            pickle.dump(inhouse_temp, file)
            pickle.dump(eventlog, file)
    except:
        LogEvent("erreur de sauvegarde des données. Impossible d'écrire sur fichier. ")


def LoadData():

    # Chargement des données enregistrées sur disque

    global times, chauffage, outside_temp, inhouse_temp, eventlog, n

    try:
        with open(FILENAME, 'rb') as file:
            times = pickle.load(file)
            chauffage = pickle.load(file)
            outside_temp = pickle.load(file)
            inhouse_temp = pickle.load(file)
            eventlog = pickle.load(file)
            n = len(eventlog)
    except:
        LogEvent("erreur dans le chargement des données sauvegardées ou fichier encore inexistant. ")


@app.route("/camera", methods=["GET", "POST"])
def camera():
    # activation/arrêt de la caméra sur l'interface web.
    # La caméra est sur un autre raspberry pi zero

    global camera, templateData

    value = request.args.get('value')
    if value == "true":
        camera = True
        LogEvent("Caméra de l'atelier activée (ON)")
    else:
        camera = False
        LogEvent("Caméra de l'atelier désactivée (OFF)")
    templateData = LoadTemplateData()

    return render_template('main.html', **templateData)


@app.route("/shutdown", methods=['POST', 'GET'])
def shutdown():

    # shutdown Raspberry Pi zero

    LogEvent("Shutdown Raspberry PI zero...)")
    SaveData()
    os.system('sudo halt')
    return


@app.route("/reboot", methods=["GET", "POST"])
def reboot():

    # reboot Raspberry Pi zero

    LogEvent("Reboot Raspberry PI zero...)")
    SaveData()
    os.system('sudo reboot')

    return


@app.route("/set_thermostat", methods=['GET', 'POST'])
def set_thermostat():

    # Thermostat, valeur max et min et activation/arrêt automatique

    global Tmin, Tmax, Thermostat

    Tmin = int(request.form.get("Tmin"))
    Tmax = int(request.form.get("Tmax"))
    checkbox = request.form.get('Thermostat')  # pour savoir si thermostat est activé ou non

    if checkbox:
        Thermostat = True
        LogEvent("Thermostat activé (ON)")
    else:
        Thermostat = False
        LogEvent("Thermostat désactivé (OFF)")

    text = "Thermostat Température min : " + str(Tmin) + " °C ;  max : " + str(Tmax) + " °C "
    LogEvent(text)

    templateData = LoadTemplateData()

    return render_template('main.html', **templateData)


@app.route("/togglerelay", methods=["GET", 'POST'])
def togglerelay():

    # Changement d'état des relais
    global Thermostat, pins, chauffage

    pin = int(request.args.get('id'))
    checked = request.args.get('checked')

    # si on commande le relai 3 (chauffage, pin22) on contrôle si Thermostat enclenché
    if pin == 22:
        if not Thermostat:
            if checked == "true":
                pins[pin]['status'] = "ON"
            elif checked == "false":
                pins[pin]['status'] = "OFF"
            else:
                print("Erreur")

            GPIO.output(pin, not GPIO.input(pin))
            pins[pin]['state'] = GPIO.input(pin)
            text = pins[pin]['name'] + " : " + pins[pin]['status']
            LogEvent(text)
        else:
            text = "Thermostat enclenché. Pas de changement manuel possible"

    else:
        if pins[pin]['status'] == "ON":
            pins[pin]['status'] = "OFF"
        else:
            pins[pin]['status'] = "ON"

        GPIO.output(pin, not GPIO.input(pin))
        pins[pin]['state'] = GPIO.input(pin)
        text = pins[pin]['name'] + " : " + pins[pin]['status']
        LogEvent(text)

    templateData = LoadTemplateData()
    logging.info(text)

    return render_template('main.html', **templateData)


@app.route("/", methods=["GET", 'POST'])
def main():
    read_temp()
    templateData = LoadTemplateData()
    return render_template('main.html', **templateData)


def read_temp():
    # lecture des senseurs de températures et ajout dans la liste des mesures

    global t, times, Tmin, Tmax, Thermostat, chauffage, Tin, Tout, MAXSIZE, pins

    for sensor_id in DS18B20.get_available_sensors():
        sensors.append(DS18B20(sensor_id))

    Tout = round(sensors[0].get_temperature(DS18B20.DEGREES_C), 2)
    Tin = round(sensors[1].get_temperature(DS18B20.DEGREES_C), 2)

    outside_temp.append(round(sensors[0].get_temperature(DS18B20.DEGREES_C), 2))
    inhouse_temp.append(round(sensors[1].get_temperature(DS18B20.DEGREES_C), 2))

    # lecture de l'heure et ajout dans la liste du temps
    now = datetime.datetime.now()
    t0 = now.strftime("%-d/%-m %H:%M")
    times.append(t0)

    # si le dictionnaire contient plus de MAXSIZE valeurs,
    # on supprime la plus ancienne de façon à garder un graphique affichable

    if len(times) > MAXSIZE:
        times.pop(0)
        outside_temp.pop(0)
        inhouse_temp.pop(0)
        chauffage.pop(0)

    if Thermostat:
        if Tin < Tmin:
            GPIO.output(22, 0)
            LogEvent("Température intérieure <= Tmin thermostat, chauffage activé (ON)")

        if Tin >= Tmax:
            GPIO.output(22, 1)
            LogEvent("Température intérieure >= Tmax thermostat, chauffage désactivé (OFF)")

    pins[22]['state'] = GPIO.input(22)

    if pins[22]['state']:
        chauffage.append(0)
        # Chauffage désactivé par thermostat

    else:
        chauffage.append(10)
        # Chauffage activé par thermostat (10 est une valeur
        # arbitraire pour un affichage sur graph en adéquation
        # avec les températures)

    message = "Mesure température intérieure : " + str(Tin) + " °C, extérieure : " + str(Tout) + " °C "
    LogEvent(message)
    SaveData()

    return


def loop():
    # Lecture de la température toute les INTERVAL_TIME_MESURE (sec))
    global INTERVAL_TIME_MESURE

    while True:
        read_temp()
        sleep(INTERVAL_TIME_MESURE)


if __name__ == "__main__":
    app.secret_key = os.urandom(12)

    LogEvent("### MyBox V4.0 (12/2021) ###")
    LogEvent("Fréquence des mesures de températures : " + str(int(INTERVAL_TIME_MESURE/60)) + " mn")
    LogEvent("Démarrage du thread de lecture des mesures")

    LoadData()

    t1 = Thread(target=loop)
    t1.start()

    app.run(host='0.0.0.0', port=80, debug=False)
