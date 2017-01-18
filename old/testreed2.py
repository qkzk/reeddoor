#!/usr/bin/env python
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import time
import smtplib


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
		mail('Ouverture porte !')
	time.sleep(0.2)
	t=t+1
	if t%20==0: #temps d'alerte x5 secondes
		longopen(t)

#fermeture de la porte
def doorclosed():
	global status_door
	global t
	if status_door==0:
		print('door stayed opened for ' + str(t/5) + ' secs')
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

time.sleep(5)
if SENDMAIL:
	mail("Script d'ouverture de porte lancé !")
while True:
    input_state = GPIO.input(18)
    if input_state == False:
    	dooropened()

    if input_state == True:
    	doorclosed()
