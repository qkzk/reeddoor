# reeddoor

Script python qui envoie différents messages à chaque ouverture et fermeture d'une porte.
Elle est surveillée à l'aide d'un capteur reed

## maintenance

EST CE QUE LE SCRIPT TOURNE ??

~~~sh
$ ssh VOTREHOST
$ ps -ef | grep python
~~~

AFFICHER UN DES LOGS LOGS PYTHON :

~~~sh
$ ssh VOTREHOST
$ tail -s 0.1 -f /home/pi/reeddoorlog/unfichierlog.log
~~~


## installation et usage

1. ssh sur le raspberry pi depuis le pc de déploiement
2. créer les dossiers `/home/pi/reed` (script) et `/home/pi/reeddoorlog`
3. Renommer `example_tokn.py` en `tokenss.py` et y éditer vos informations
4. `$ chmod +x ./deploy.sh`
5. Déployer avec `./deploy.sh`

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
2. mail et installation
3. logs locaux
4. upload status adafruit io
5. plantage !!! DONE - sept 2016

  pb : connexion avec smtp plante : create_connexion
  socket.error: [Errno 101] Network is unreachable
  solution long terme : si le smtp plante, try execpt un error et pas planter !!!!!

6. connexion via socket au rpi2 : octobre 2016
    envoi des msg : DONE
    refresh continu
7. bugs
8. bugs
10. janvier 2017 : ajout d'autres feed aio pour clarifier le dashboard
11. GITHUB first commit
12. septembre 2019 : je remet le nez là dedans. Bcp de choses ont changé je vais sûrement tout réécrire.
13. septembre 2019 : réécriture complète des fonctions en Python 3.4 (dernière version sur Debian Jessie).
	* création d'une classe pour la porte,
	* mesure des temps d'ouverture plus fidèle
	* un seul principe pour les logs : rotating file handler
	* possibilité d'un mode verbose si besoin de deboguer

	Reste à améliorer le principe des logs, trop de messages, en particulier mqtt... trouver un moyen d'alerter si le broker est down
14. 2020/01/28 : nettoyage du code (en partie), création d'un script de déploiement.


TODO

* connaissance du temps de down via une lecture des logs (le dernier message de statut enregirstré est daté de ...)
* quand la porte s'ouvre, envoyer la dernière date connue de fermeture (paranioa mode)
* limiter la fréquence d'écriture à un fichier...
