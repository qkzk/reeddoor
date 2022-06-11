#!/usr/bin/python3


"""
title: reed_logguer
author: qkzk

enregistre les ouvertures et fermetures d'une porte via plusieurs média :

* log local
* envoi d'un mail à gmail
* envoi d'un message à un broker mqtt

* chaque erreur est enregistrée (mqtt ne répond pas, gmail injoignable etc.)
* on enregistre aussi les durées d'ouverture de la porte (simple compteur)
    Quand la porte reste ouverte longtemps on envoit bcp de messages, ce n'est
    pas normal
"""

import logging
import time
import smtplib
import sys
from logging import Logger
from logging.handlers import RotatingFileHandler

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

import tokenss

LOGFILE_PRINT = "/home/pi/reeddoorlog/print.log"
LOGFILE_OPENINGS = "/home/pi/reeddoorlog/ouvertures.log"
LOGFILE_ERRORS = "/home/pi/reeddoorlog/reed_logguer_errors.log"
LOGFILE_STATUS = "/home/pi/reeddoorlog/up.log"

MQTT_BROKER_ADDRESS = "192.168.1.26"
MQTT_TOPIC = "qdoor"

GPIO_PIN = 18

door_status = int
DOOR_IS_OPENED = 1
DOOR_IS_CLOSED = 0

TICK_TIME = 0.2  # second


def parse_args() -> bool:
    """
    Récupère et interprète les arguments passés lors de l'appel.
    Si on repère une des lettres de verbose, le mode est activé.
    Si "verbose" dans l'argument console, affiche le texte
    Sinon on n'imprimera rien dans la console
    """
    return len(sys.argv) > 1 and sys.argv[1] in "VERBOSEverbose"


def setup_app_log(logfile: str) -> Logger:
    """
    Crée un logguer avec rotation des fichiers logs
    Le nom du logguer est le nom du fichier dans lequel il enregistre.
    On loggue bcp (c'est le but de ce script... donc il faut plusieurs logguers)
    """
    logname = logfile.split("/")[-1]
    log_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s"
    )
    handler = RotatingFileHandler(
        logfile,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding=None,
        delay=False,
    )
    handler.setFormatter(log_formatter)
    handler.setLevel(logging.INFO)

    app_log = logging.getLogger(logname)
    app_log.setLevel(logging.INFO)
    app_log.addHandler(handler)

    return app_log


class Announcer:
    loggers: dict[str, Logger] = {
        "log_opening": setup_app_log(LOGFILE_OPENINGS),
        "log_errors": setup_app_log(LOGFILE_ERRORS),
        "log_uptime_door": setup_app_log(LOGFILE_STATUS),
        "log_stdout": setup_app_log(LOGFILE_PRINT),
    }

    def __init__(self, verbose: bool):
        self.verbose = print if verbose else lambda _: None

    def send_mqtt(self, data_type, data):
        """
        Envoie un message au broker du raspberry via mqtt
        Log les erreurs eventuelles
        """
        try:
            client = mqtt.Client("rpi1_qnas")
            client.on_connect = self.on_connect
            client.on_message = self.on_message
            client.connect(MQTT_BROKER_ADDRESS)
            client.loop_start()
            client.publish(MQTT_TOPIC + "/{}".format(data_type), data)
            client.disconnect()
            client.loop_stop()
        except Exception:
            msg = "{} \nMQTT error".format(time.strftime("%Y-%m-%d %H:%M:%S"))
            self.loggers["log_stdout"].warning(msg)
            self.loggers["log_errors"].warning(msg)
            self.verbose(msg)

    def on_connect(self, client, userdata, flags, rc):
        """
        On log les connexions à mqtt
        """
        msg = "Connected flags {} result code {} client1_id {}".format(
            flags, rc, client
        )
        self.loggers["log_stdout"].warning(msg)
        self.verbose(msg)

    def on_message(self, client, userdata, message):
        """
        On log les messages reçus par mqtt
        """
        msg = "message received {}".format(str(message.payload.decode("utf-8")))
        self.loggers["log_stdout"].warning(msg)
        self.verbose(msg)

    def mail(self, mailmsg):
        """
        Rédige et envoie un email via gmail.
        Log les erreurs
        TODO : pourquoi les caractères non ascii font planter ?
        probleme avec le mimetype, faudrait préciser des trucs, j'ai pas tt compris
        sources :
        https://petermolnar.net/not-mime-email-python-3/
        https://fr.wikipedia.org/wiki/Multipurpose_Internet_Mail_Extensions
        """
        try:
            email_subject = "MSG d'alerte du Raspberry Pi : porte d'entree"
            recipient = tokenss.recipient
            now_string = time.strftime("%Y-%m-%d %H:%M:%S")
            body_of_email = "{} \n{}".format(now_string, mailmsg)

            session = smtplib.SMTP("smtp.gmail.com", 587)
            session.ehlo()
            session.starttls()
            session.login(tokenss.GMAIL_USERNAME, tokenss.GMAIL_PASSWORD)

            headers = "\r\n".join(
                [
                    "from: {}".format(tokenss.GMAIL_USERNAME),
                    "subject: {}".format(email_subject),
                    "to: {}".format(recipient),
                    "mime-version: 1.0",
                    "content-type: text/html",
                ]
            )

            content = headers + "\r\n\r\n" + body_of_email
            session.sendmail(tokenss.GMAIL_USERNAME, recipient, content)

        except Exception:
            msg = "{} \nmail send error".format(time.strftime("%Y-%m-%d %H:%M:%S"))
            self.loggers["log_stdout"].warning(msg)
            self.loggers["log_errors"].warning(msg)
            self.verbose(msg)

    def announce_itself(self):
        self.verbose("starting...")
        msg = "Lancement du script reed door"
        time.sleep(5)
        self.loggers["log_opening"].warning("%s", msg)
        self.loggers["log_stdout"].warning(msg)
        self.send_mqtt("ouverture", "lancement")
        self.mail(msg)
        self.verbose(msg)

    def long_open(self, duration: int):
        msg = "door opened long time"
        self.loggers["log_stdout"].warning(msg)
        self.loggers["log_uptime_door"].warning("0")
        self.send_mqtt("ouverture", "long {}".format(duration))
        self.send_mqtt("status", DOOR_IS_OPENED)
        self.mail("La porte est ouverte depuis {} secondes".format(duration))
        self.verbose(msg)

    def door_stayed_opened(self, duration: int):
        msg = "La porte est restee ouverte {} secondes".format(duration)
        self.loggers["log_opening"].warning("%s", msg)
        self.loggers["log_stdout"].warning(msg)
        mqtt_msg = "closed {}".format(duration)
        self.send_mqtt("ouverture", mqtt_msg)
        self.mail(msg)
        self.verbose(msg)

    def update_status(self, status: door_status):
        self.loggers["log_uptime_door"].warning(str(status))
        self.send_mqtt("statusdoor", status)

    def door_opened(self):
        msg = "door opened NOW !"
        self.loggers["log_opening"].warning("%s", "Ouverture porte")
        self.loggers["log_stdout"].warning(msg)
        self.send_mqtt("ouverture", "open")
        self.send_mqtt("statusdoor", DOOR_IS_OPENED)
        self.mail("ouverture porte !")
        self.verbose(msg)

    def door_still_opened(self, duration: int):
        self.loggers["log_stdout"].warning("door opened %i secs", duration)
        self.verbose("door opened {} secs".format(duration))


class Door:
    """gère les états de la porte."""

    def __init__(self, exporter: Announcer):
        self.exporter = exporter

        self.tick_open = 0
        self.tick_close = 0
        self.door_status = DOOR_IS_CLOSED
        self.last_opened = 0
        self.last_closed = 0

    def opening_duration(self):
        """
        Calcule et arrondit une durée d'ouverture en seconde.
        """
        return round(time.time() - self.last_opened)

    def is_opened(self):
        """
        Appelé quand le capteur détecte que la porte est fermée.
        Compte depuis combien de temps et si on dépasse le seuil envoie des
        mails.
        Log tout ce qu'il peut, c'est le statut critique.
        """
        self.door_status = DOOR_IS_OPENED
        self.tick_close = 0

        if self.tick_open == 0:
            self.last_opened = time.time()
            self.exporter.door_opened()
        else:
            self.exporter.door_still_opened(self.opening_duration())
        time.sleep(TICK_TIME)
        self.tick_open += 1
        if self.tick_open % 20 == 0:
            self.exporter.long_open(self.opening_duration())

    def is_closed(self):
        """
        Appelé quand la porte est fermée.
        Log les états et publie dans le fichier dédié à ce tracking
        """
        if self.door_status == DOOR_IS_OPENED:
            self.exporter.door_stayed_opened(self.opening_duration())

        self.door_status = DOOR_IS_CLOSED  # porte fermee
        self.tick_open = 0
        time.sleep(TICK_TIME)
        self.tick_close += 1
        if self.tick_close % 40 == 0:  # fermee depuis 5s
            self.exporter.update_status(DOOR_IS_CLOSED)


def gpio_input(door: Door):
    """read status and alert"""
    input_state = GPIO.input(GPIO_PIN)
    if input_state:
        door.is_closed()
    else:
        door.is_opened()


def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    verbose = parse_args()
    announcer = Announcer(verbose)
    door = Door(announcer)

    announcer.announce_itself()
    while True:
        gpio_input(door)


if __name__ == "__main__":
    main()
