#!/usr/bin/env python
# -*- coding: utf-8 -*-

#1 test
#2 mail et installation
#3 logs locaux 
#4 upload status adafruit io

import RPi.GPIO as GPIO
import time
import smtplib
import logging

#adaiot
# Import library and create instance of REST client.
from Adafruit_IO import Client
aio = Client('85f3a92915624c0090ad67be023e618f')


GPIO.setmode(GPIO.BCM)

GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#variables
status_door = 1 # porte fermee 
t = 0 #compteur de durée d'ouverture

#doit on envoyer des mails ?
SENDMAIL = True

#alerte ouverture longue
def longopen(t):
	print('door opened long time')
	if SENDMAIL:
		mail('la porte est ouverte depuis ' + str(t/5) + ' secondes')

#ouverture de la porte
def dooropened():
	global t
	global status_door
	status_door = 0 #porte ouverte
	print('door opened '+ str(t/5) + ' secs')

	if t==0 and SENDMAIL:
		# Send the value 100 to a feed called 'Foo'.
		aio.send('Door', 0)
		mail('Ouverture porte !')
		logging.warning('%s', 'Ouverture porte')
	time.sleep(0.2)
	t=t+1
	if t%20==0: #temps d'alerte x5 secondes
		longopen(t)

#fermeture de la porte
def doorclosed():
	global status_door
	global t
	if status_door==0:
		aio.send('Door', 1)
		print('door stayed opened for ' + str(t/5) + ' secs')
		logging.warning('%s', 'La porte est restée ouverte ' + str(t/5) + ' secondes')
		if SENDMAIL:
			mail('la porte est restée ouverte ' + str(t/5) + ' secondes')
	status_door=1#porte fermee
	t=0
	time.sleep(0.2)


# mail
def mail(mailmsg):  
     # Login, password, contenu
     GMAIL_USERNAME = 'leclemenceau'
     GMAIL_PASSWORD = 'nickelpe160'
     
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



############################### EXECUTION ####################################


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



#boucle du gpio
while True:
    input_state = GPIO.input(18)
    if input_state == False:
    	dooropened()

    if input_state == True:
    	doorclosed()
