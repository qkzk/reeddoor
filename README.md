#reeddoor
script python qui envoie différents messages à chaque ouverture et fermeture d'une porte.
Elle est surveillée à l'aide d'un capteur reed

## maintenance

EST CE QUE LE SCRIPT TOURNE ??  
ps -ef | grep python


AFFICHER LES LOGS PYTHON :  
tail -s 0.1 -f /home/pi/reeddoorlog/reeddoor.pi.log


AFFICHER LES LOGS DU SCRIPT LUI MEME :
nano reeddoorlog/reeddoor.log


## installation et usage

1. copier le script à la racine  
1. créer le crontab
1. rebooter, checker les logs (voir plus haut)  
1. renommer `token_example.py` en `token.py` et l'éditer  
1. le script envoie un mail à l'adresse indiquée dans token.py à chaque lancement
1. il tente de se connecter à un server socket régulièrement pour indiquer son état
1. il tente d'envoyer des msg à adafruit_IO
1. il tente d'envoyer des mails à chaque ouverture  


CRONTAB sudo crontab -e  
`@reboot /usr/bin/python /home/pi/testreed.py >> /home/pi/reeddoorlog/reeddoor.pi.log 2>&1`

LANCER MANUELLEMENT
`sudo /usr/bin/python /home/pi/testreed.py >> /home/pi/reeddoorlog/reeddoor.pi.log 2>&1 &`


-----------------

Principe :

RPI -> GPIO -> capteur REED (magnetique) sur la porte
RPI -> WIFI mail & adafruit.io
RPI -> 2 logs locaux (OUT du script, logs internes aux script)
RPI -> connexion socket au RPI Camera (etat ~2s de refresh, dernier msg)

au boot : lancé par un crontab et log les affichages du script lui meme

1. envoie un mail (exception si pas possible) pour indiquer son lancement
2. à chaque ouverture : envoie un mail, log local, change de statut sur adafruit.io
3. si ouverture longue : log local, envoie un mail
4. à chaque fermeture : envoie un mail, log local, change de statut sur adafruit.io

GPIO :
	pin 18 (pull_up_down)
	pin GND
