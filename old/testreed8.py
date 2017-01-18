#!/usr/bin/env python
# -*- coding: utf-8 -*-


#                              test reed

# programme python a installer dans /home/pi

# lit un capteur magnétique type REED sur la porte d'entrée
# connecté au GPIO 18 (signal) et GPIO Ground
# lancé par un crontab

# à chaque changement d'état du capteur il lance une fonction
# dooropened() si la porte est ouverte 1 : 
# doorclosed() si la porte est fermée 0
# faille de sécurité un aimant bien placé empechera le capteur de réagir

# au lancement du script il envoie un mail
# dooropened : 	lance un timer (toutes les 5 sec un msg)
# 				lance un msg : socket, log & mail
# doorclosed :	envoie un msg avec la durée d'ouverture transmise par dooropened

# statut : 		qqsoit l'etat il envoie un up toutes les 5 sec par socket

# mail : 		utilise le gmail de google
# socket :		socketserver sur RPI2 (camera) (écoute et parse les msg, réagit en fct (gif des ouvertures))
# logs : 		lisibles dans /home/pi/reeddoorlog/
# 				reeddor5.pi.log : logs des messages enregristrés
# 				reeddoor.log :	log des connexions
# adaiot : 		publie les chgts d'état sur adaiot

# 									CHANGELOG

# 1 test : juillet 2016
# 2 mail et installation
# 3 logs locaux 
# 4 upload status adafruit io
# 5 plantage !!! DONE - sept 2016
# 		pb : connexion avec smtp plante : create_connexion
# 		socket.error: [Errno 101] Network is unreachable
# 		solution long terme : si le smtp plante, try execpt un error et pas planter !!!!!
# 6 connexion via socket au rpi2 : octobre 2016
# 		envoi des msg : DONE
# 		refresh continu

# 										TODO
# separer les messages logs dans 3 fichiers : etats, socket, mail
# ameliorer socket pour gérer la connexion et s'assurer que les chgts d'état sont reportés
# dans socket créer visualisation serveur
# clarifier le code, séparer les modules utilisables dans d'autres fichiers (mail msg etc.)
# deporter les identifiants dans un autre fichier et les importer
# publier sur GITHUB pour archivage



###################################### IMPORTS  ##############################################

import RPi.GPIO as GPIO
import time
from time import strftime
import smtplib
import logging
import socket
from Adafruit_IO import Client


######################################## FONCTIONS ############################################


#alerte ouverture longue
#parameters : t. duree d'ouverture = 0.2t s
def longopen(t):
	print('door opened long time')
	socketconnect(' La porte est ouverte depuis ' + str(t/5) + ' secondes ')
	if SENDMAIL:
		mail('La porte est ouverte depuis ' + str(t/5) + ' secondes')

#ouverture de la porte
#parameters : aucun
#compte la durée d'ouverture et la publie
#lance longopen a intervalle regulier
#check le statut
def dooropened():
	global t
	global status_door
	global f
	status_door = 0 #porte ouverte
	f=0 #reset la durée de fermeture
	print('door opened '+ str(t/5) + ' secs')

	if t==0:
		# Envoie la valeur 0 au feed nommé 'Door'
		aio.send('Door', 0)
		logging.warning('%s', 'Ouverture porte')
		if SENDMAIL:
			mail(' Ouverture porte !')
		socketconnect(' Ouverture porte ! ')
	time.sleep(0.2)
	t=t+1
	if t%20==0: #temps d'alerte x5 secondes
		longopen(t)
		socketconnect(str(time.time())+" up O") #envoie un msg de up au socketserver avec le temps en s

#fermeture de la porte
#parameters : aucun
#check le statut
def doorclosed():
	global status_door
	global t #contient la duree d'ouverture de la porte
	global f #durée de fermeture de la porte
	if status_door==0:
		#envoie la valeur 1 au feed nommé "Door"
		aio.send('Door', 1)
		print('door stayed opened for ' + str(t/5) + ' secs')
		logging.warning('%s', 'La porte est restée ouverte ' + str(t/5) + ' secondes')
		if SENDMAIL:
			mail('La porte est restée ouverte ' + str(t/5) + ' secondes')
		socketconnect(' La porte est restée ouverte ' + str(t/5) + ' secondes ')
	status_door=1 	#porte fermee
	t=0
	time.sleep(0.2)
	f=f+1
	if f%20==0: #fermee depuis 5s
		socketconnect(str(time.time())+" up 1") #envoie un msg de up au socketserver

	


# mail
# parmeters : mailmsg = le corps du mail
# appelé par les différentes fct (lancement, ouverture, fermeture, longue ouverture)
def mail(mailmsg):  
	try:
		GMAIL_USERNAME = 'leclemenceau'
		GMAIL_PASSWORD = 'wtwwuqwtyrmuorrk'
		
		email_subject = "MSG d'alerte du Raspberry Pi : porte d'entrée"
		recipient = "qu3nt1n@gmail.com"
		body_of_email = mailmsg

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
	     
	    #logging.info('mail envoye') #log
	except IOError:
		print "socket.error impossible d'envoyer le mail"
		pass
		#ajouter logs dans le fichier normal de l'exception, détailler l'exception
	except :
		raise
	    # Login, password, contenu

#connexion au socket du rpi2Camera log si connexion impossible
#parameters : socketmsg le corps du msg
#appelé régulierement pour check le statut (open, close)
#appelé à intervalle régulier (heartbeat)
def socketconnect(socketmsg):
	mylist = [socketmsg] #met le msg dans une liste
	mylist.append(strftime("%Y-%m-%d %H:%M:%S"))

	print mylist[0] #affiche le msg envoyé - à retirer une fois terminé
	address = '192.168.0.30' #rpiCamera
	port = 8089 #port random, meme que server
	clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #parametres du socket
	try: #pour eviter de planter si le server est down
		clientsocket.connect((address, port)) #ouvre la connexion
		clientsocket.send(str(mylist[1])+" "+str(mylist[0])) #envoie le msg
	except Exception as e:
		logging.warning("Erreur de connexion SOCKET : %s:%d. Exception is %s" % (address, port, e)) #log un msg si erreur
	finally:
		clientsocket.close() #dans tous les cas ferme la connexion

############################### EXECUTION ####################################

#CONFIGURATION

#adaiot
# Import library and create instance of REST client.
aio = Client('85f3a92915624c0090ad67be023e618f')

#GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#variables globales
status_door = 1 # porte fermee 
t = 0 #compteur de durée d'ouverture unité : 0.2s
f = 0 #compteur de durée de fermeture unité : 0.2s

#doit on envoyer des mails ?
SENDMAIL = True

#logging
logger = logging.getLogger() #lance le logguer
logger.setLevel(logging.DEBUG) #log a partir du niveau debug
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') #cree un format
fh = logging.FileHandler("/home/pi/reeddoorlog/reeddoor.log") #fichier de destination
fh.setFormatter(formatter) # add formatter to fh
logger.addHandler(fh)

#lancement du script
time.sleep(5) #pour que la connexion wifi soit établie
logging.warning('%s', 'Lancement du script ReedDoor')
if SENDMAIL:
	mail("Script d'ouverture de porte lancé !") #information du reboot et de la bonne connexion
socketconnect("Script d'ouverture de porte lancé !")


############################# boucle infinie du GPIO ########################
while True:
    input_state = GPIO.input(18)
    if input_state == False:
    	dooropened()

    if input_state == True:
    	doorclosed()
