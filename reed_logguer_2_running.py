#!/usr/bin/env python
# coding=utf-8


'''
découpe du reedtestxx.py en deux scripts au moins

script1 : reed_data_logguer.py
script2 : reed_data_parser.py

toute la communication entre eux passe par un broker mosquitto

script1 : chgt d'état (ou update) -> mqtt broker topic /reed/status et reed/ouverture + log local

script2 : update état puis publish - mail, adaiot, mqtt to qnas etc

----

probleme : aio fait planter le script silencieusement.

résolution proposée : concentrer tout aio dans qnas et ne transferer que mail & mqtt à qnas
faire la meme chose à dht22 : mqtt only. Pas non plus de socket

restera un soucis : relancer aio si nécessaire. Envisager un retour d'info d'aio et des relances.

----

ici intégrer mail.
'''

import RPi.GPIO as GPIO
import time
from time import strftime
import logging
import paho.mqtt.client as mqtt

import smtplib
import tokenss

# globals
fichier_log = "/home/pi/reeddoorlog/reed_logguer_errors.log"
############ fonctions de communication ###############
'''
logs
'''

def logUpDoor(etat):
    # log l'état dans un fichier local

	f = '/home/pi/reeddoorlog/up.log'
	temps = str(time.time())
	#nettoyage des logs avant chaque ajout
	lines = open(f).readlines()
	if len(lines)>=1000:
		open(f, 'w').writelines(lines[len(lines)-999:len(lines)]) #ne garde que les 9 dernieres lignes
	up_file= open(f,"a") #mode append
	up_file.write("\n"+temps + " " + etat) #ajoute
	up_file.close()

'''
mqtt
'''

def on_connect(client, userdata, flags, rc):
    m="Connected flags"+str(flags)+"result code "\
    +str(rc)+"client1_id  "+str(client)
    print(m)

def on_message(client1, userdata, message):
    print("message received {}".format(str(message.payload.decode("utf-8"))))

def send_mqtt(data_type, data):
    try:
        broker_address="192.168.1.26"
        client2 = mqtt.Client("rpi1_qnas")    #create new instance
        client2.on_connect= on_connect        #attach function to callback
        client2.on_message=on_message        #attach function to callback
        client2.connect(broker_address)      #connect to broker
        client2.loop_start()    #start the loop
        client2.publish("reeddoor/{}".format(data_type),data) # sent the data
        client2.disconnect()
        client2.loop_stop()
    except Exception as e:
        msg = "{} \nMQTT error".format(time.strftime("%Y-%m-%d %H:%M:%S"))
        print(msg)
        logerrors(msg)
        pass

# mail
def mail(mailmsg):
    try:
        GMAIL_USERNAME = tokenss.GMAIL_USERNAME
        GMAIL_PASSWORD = tokenss.GMAIL_PASSWORD

        email_subject = "MSG d'alerte du Raspberry Pi : porte d'entrée"
        recipient = tokenss.recipient
        body_of_email = "{} \n{}".format(time.strftime("%Y-%m-%d %H:%M:%S"), mailmsg)

        session = smtplib.SMTP('smtp.gmail.com', 587)
        session.ehlo()
        session.starttls()
        session.login(GMAIL_USERNAME, GMAIL_PASSWORD)

        headers = "\r\n".join(["from: " + GMAIL_USERNAME,
        "subject: " + email_subject,
        "to: " + recipient,
        "mime-version: 1.0",
        "content-type: text/html"])

        # body_of_email can be plaintext or html!
        content = headers + "\r\n\r\n" + body_of_email
        session.sendmail(GMAIL_USERNAME, recipient, content) # commande d'envoi du mail
    except Exception as e:
        msg = "{} \nmail send error".format(time.strftime("%Y-%m-%d %H:%M:%S"))
        print(msg)
        logerrors(msg)
        pass

def logerrors(msg):
    global fichier_log
    lines = open(fichier_log).readlines()
    #ne garde que les 5000 dernieres lignes
    if len(lines)>=5000:
        open(fichier_log, 'w').writelines(lines[len(lines)-4999:len(lines)])
    #ajout d'une ligne au log
    hs = open(fichier_log,"a")
    hs.write(msg + "\n")
    hs.close()


######## fonctions du capteur #######
def longopen(t):
	print('door opened long time')
	send_mqtt("ouverture", 'long ' + str(t/5) )
	mail('La porte est ouverte depuis ' + str(t/5) + ' secondes')


def dooropened():
	global t
	global status_door
	global f
	status_door = 0 #porte ouverte
	f=0 #reset la durée de fermeture
	print('door opened '+ str(t/5) + ' secs')

	if t==0:
		# Envoie la valeur 0 au feed nommé 'Door'
		app_log.warning('%s', 'Ouverture porte')
		send_mqtt("ouverture", 'open')
		send_mqtt("statusdoor", 0)
		mail('ouverture porte !')
	time.sleep(0.2)
	t=t+1
	if t%20==0: #temps d'alerte x5 secondes
		longopen(t)
		logUpDoor('0')
		send_mqtt("status", 0)

#fermeture de la porte
#parameters : aucun
#check le statut
def doorclosed():
	global status_door
	global t #contient la duree d'ouverture de la porte
	global f #durée de fermeture de la porte
	if status_door==0:
		print('door stayed opened for ' + str(t/5) + ' secs')
		app_log.warning('%s', 'La porte est restée ouverte ' + str(t/5) + ' secondes')
		send_mqtt("ouverture", 'closed ' + str(t/5))
		mail('La porte est restée ouverte ' + str(t/5) + ' secondes')
	status_door=1 	#porte fermee
	t=0
	time.sleep(0.2)
	f=f+1
	if f%40==0: #fermee depuis 5s
		logUpDoor('1')
		send_mqtt("statusdoor", 1)


############################### EXECUTION ####################################

#CONFIGURATION

#GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#variables globales
status_door = 1 # porte fermee
t = 0 #compteur de durée d'ouverture unité : 0.2s
f = 0 #compteur de durée de fermeture unité : 0.2s

# logging avec rotating log limite a 5 mb
from logging.handlers import RotatingFileHandler
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = '/home/pi/reeddoorlog/print.log'

my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024,
                                 backupCount=2, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(my_handler)

#lancement du script
time.sleep(5) #pour que la connexion wifi soit établie
app_log.warning('%s', 'Lancement du script ReedDoor')
send_mqtt("ouverture", 'lancement')
mail('Lancement du script ReedDoor')


############################# boucle infinie du GPIO ########################
while True:
    input_state = GPIO.input(18)
    if input_state == False:
    	dooropened()

    if input_state == True:
    	doorclosed()
