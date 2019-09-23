# reeddoor

script python qui envoie différents messages à chaque ouverture et fermeture d'une porte.
Elle est surveillée à l'aide d'un capteur reed

## maintenance

EST CE QUE LE SCRIPT TOURNE ??
~~~sh
$ ps -ef | grep python
~~~

AFFICHER UN DES LOGS LOGS PYTHON :
~~~sh
$ tail -s 0.1 -f /home/pi/reeddoorlog/unfichierlog.log
~~~


## installation et usage

1. copier le dossier dans `/home/pi`
1. créer le crontab
1. rebooter, checker les logs (voir plus haut)
1. renommer `token_example.py` en `tokenss.py` et l'éditer
1. le script envoie un mail à l'adresse indiquée dans tokenss.py à chaque lancement
1. il tente de se connecter à un server socket régulièrement pour indiquer son état
1. il tente d'envoyer des msg à adafruit_IO
1. il tente d'envoyer des mails à chaque ouverture


CRONTAB

~~~sh
$ sudo crontab -e
~~~
Ajouter :
~~~
@reboot sleep 30 && /usr/bin/python3 reed_logguer_3_dev.py >> /home/pi/reeddoorlog/print.log 2>&1
~~~
LANCER MANUELLEMENT

~~~sh
$ sudo /usr/bin/python3 reed_logguer_3_dev.py >> /home/pi/reeddoorlog/print.log 2>&1
~~~

---

## Principe :

RPI -> GPIO -> capteur REED (magnétique) sur la porte
RPI -> WIFI mail & broker mqtt
RPI -> 4 logs locaux (stdout du script, ouvertures, up, errors)

au boot : lancé par un crontab et log les affichages du script lui meme

1. envoie un mail (exception si pas possible) pour indiquer son lancement
2. à chaque ouverture : envoie un mail, log local, envoie un msg au broker mqtt
3. si ouverture longue : log local, envoie un mail
4. à chaque fermeture : envoie un mail, log local, envoi un msg au broker mqtt

GPIO :
	pin 18 (pull_up_down)
	pin GND


---


## CHANGELOG

1. test : juillet 2016
1. mail et installation
1. logs locaux
1. upload status adafruit io
1. plantage !!! DONE - sept 2016
pb : connexion avec smtp plante : create_connexion
socket.error: [Errno 101] Network is unreachable
solution long terme : si le smtp plante, try execpt un error et pas planter !!!!!
1. connexion via socket au rpi2 : octobre 2016
envoi des msg : DONE
refresh continu
1. bugs
1. bugs
1. janvier 2017 : ajout d'autres feed aio pour clarifier le dashboard
1. GITHUB first commit
2. septembre 2019 : je remet le nez là dedans. Bcp de choses ont changé je vais sûrement tout réécrire.
3. septembre 2019 : réécriture complète des fonctions en Python 3.4 (dernière version sur Debian Jessie).
	* création d'une classe pour la porte,
	* mesure des temps d'ouverture plus fidèle
	* un seul principe pour les logs : rotating file handler
	* possibilité d'un mode verbose si besoin de debuggé

	Reste à améliorer le principe des logs, trop de messages, en particulier mqtt... trouver un moyen d'alerter si le broker est down


TODO

* connaissance du temps de down via une lecture des logs (le dernier message de statut enregirstré est daté de ...)
* quand la porte s'ouvre, envoyer la dernière date connue de fermeture (paranioa mode)
* limiter la fréquence d'écriture à un fichier...
