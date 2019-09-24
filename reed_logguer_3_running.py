'''
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
'''

# std library
import logging
import time
import smtplib
import sys
from logging.handlers import RotatingFileHandler

# community
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

# self
import tokenss

# globals
logfile_print = '/home/pi/reeddoorlog/print.log'
logfile_ouvertures = '/home/pi/reeddoorlog/ouvertures.log'
logfile_errors = "/home/pi/reeddoorlog/reed_logguer_errors.log"
logfile_status = '/home/pi/reeddoorlog/up.log'

broker_address = "192.168.1.26"


##############################################################################
################################### mqtt #####################################
##############################################################################


def on_connect(client, userdata, flags, rc):
    '''
    On log les connexions à mqtt
    '''
    msg = "Connected flags {} result code {} client1_id {}".format(flags,
                                                                   rc,
                                                                   client)
    log_stdout.warning(msg)
    if verbose:
        print(msg)


def on_message(client, userdata, message):
    '''
    On log les messages reçus par mqtt
    '''
    msg = "message received {}".format(str(message.payload.decode("utf-8")))
    log_stdout.warning(msg)
    if verbose:
        print(msg)


def send_mqtt(data_type, data):
    '''
    Envoie un message au broker du raspberry via mqtt
    Log les erreurs eventuelles
    '''
    try:
        client = mqtt.Client("rpi1_qnas")  # create new instance
        client.on_connect = on_connect  # attach function to callback
        client.on_message = on_message  # attach function to callback
        client.connect(broker_address)  # connect to broker
        client.loop_start()  # start the loop
        client.publish("reeddoor/{}".format(data_type), data)  # sent the data
        client.disconnect()
        client.loop_stop()
    except Exception as e:
        msg = "{} \nMQTT error".format(time.strftime("%Y-%m-%d %H:%M:%S"))
        log_stdout.warning(msg)
        if verbose:
            print(msg)
        log_errors.warning(msg)


##############################################################################
################################### mail #####################################
##############################################################################


def mail(mailmsg):
    '''
    Rédige et envoie un email via gmail.
    Log les erreurs
    TODO : pourquoi les caractères non ascii font planter ?
    probleme avec le mimetype, faudrait préciser des trucs, j'ai pas tt compris
    sources :
    https://petermolnar.net/not-mime-email-python-3/
    https://fr.wikipedia.org/wiki/Multipurpose_Internet_Mail_Extensions
    '''
    try:
        GMAIL_USERNAME = tokenss.GMAIL_USERNAME
        GMAIL_PASSWORD = tokenss.GMAIL_PASSWORD

        email_subject = "MSG d'alerte du Raspberry Pi : porte d'entree"
        recipient = tokenss.recipient
        now_string = time.strftime("%Y-%m-%d %H:%M:%S")
        body_of_email = "{} \n{}".format(now_string, mailmsg)

        session = smtplib.SMTP('smtp.gmail.com', 587)
        session.ehlo()
        session.starttls()
        session.login(GMAIL_USERNAME, GMAIL_PASSWORD)

        headers = "\r\n".join(["from: {}".format(GMAIL_USERNAME),
                               "subject: {}".format(email_subject),
                               "to: {}".format(recipient),
                               "mime-version: 1.0",
                               "content-type: text/html"])

        # body_of_email can be plaintext or html!
        content = headers + "\r\n\r\n" + body_of_email
        # commande d'envoi du mail
        session.sendmail(GMAIL_USERNAME, recipient, content)
    except Exception as e:
        msg = "{} \nmail send error".format(time.strftime("%Y-%m-%d %H:%M:%S"))
        log_stdout.warning(msg)
        if verbose:
            print(msg)
        log_errors.warning(msg)


##############################################################################
################################### logs #####################################
##############################################################################


def setup_app_log(logfile):
    '''
    Crée un logguer avec rotation des fichiers logs
    Le nom du logguer est le nom du fichier dans lequel il enregistre.
    On loggue bcp (c'est le but de ce script... donc il faut plusieurs logguers)
    '''
    logname = logfile.split("/")[-1]
    log_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    my_handler = RotatingFileHandler(logfile, mode='a',
                                     maxBytes=5*1024*1024, backupCount=2,
                                     encoding=None, delay=0)
    my_handler.setFormatter(log_formatter)
    my_handler.setLevel(logging.INFO)

    # app_log = logging.getLogger('root')
    app_log = logging.getLogger(logname)
    app_log.setLevel(logging.INFO)
    app_log.addHandler(my_handler)

    return app_log


def parse_args():
    '''
    Récupère et interprète les arguments passés lors de l'appel.
    Si on repère une des lettres de verbose, le mode est activé.
    Si "verbose" dans l'argument console, affiche le texte
    Sinon on n'imprimera rien dans la console
    '''
    argugments = sys.argv
    verbose = False
    if len(sys.argv) >= 2 and sys.argv[1] in "VERBOSEverbose":
        print("verbose !")
        verbose = True

    return verbose


##############################################################################
################################### reed  ####################################
##############################################################################


class Door():
    """gère les états de la porte."""

    def __init__(self):
        self.tick_ouverture = 0
        self.tick_fermeture = 0
        self.door_status = 1
        self.last_opened = None
        self.last_closed = None

    def duree_ouverture(self):
        '''
        Calcule et arrondit une durée d'ouverture en seconde.
        '''
        return round(time.time() - self.last_opened)

    def long_open(self):
        '''
        Exécutée quand la porte reste longtemps ouverte.
        Log les états partout et envoie un mail.
        '''
        duree = self.duree_ouverture()
        log_stdout.warning('door opened long time')
        if verbose:
            print(msg)
        send_mqtt("ouverture", 'long {}'.format(duree))
        mail('La porte est ouverte depuis {} secondes'.format(duree))

    def door_opened(self):
        '''
        Appelé quand le capteur détecte que la porte est fermée.
        Compte depuis combien de temps et si on dépasse le seuil envoie des
        mails.
        Log tout ce qu'il peut, c'est le statut critique.
        '''
        self.door_status = 0  # porte ouverte
        self.tick_fermeture = 0  # reset la durée de fermeture

        if self.tick_ouverture == 0:
            # Envoie la valeur 0 au feed nommé 'Door'
            self.last_opened = time.time()
            log_ouverture.warning('%s', 'Ouverture porte')
            send_mqtt("ouverture", 'open')
            send_mqtt("statusdoor", 0)
            mail('ouverture porte !')
            log_stdout.warning('door opened NOW !')
            if verbose:
                print(msg)
        else:
            log_stdout.warning('door opened {} secs'.format(
                self.duree_ouverture()))
            if verbose:
                print('door opened {} secs'.format(
                    self.duree_ouverture()))
        time.sleep(0.2)
        self.tick_ouverture += 1
        if self.tick_ouverture % 20 == 0:
            # temps d'alerte x5 secondes
            self.long_open()
            log_uptime_door.warning('0')
            send_mqtt("status", 0)

    def door_closed(self):
        '''
        Appelé quand la porte est fermée.
        Log les états et publie dans le fichier dédié à ce tracking
        '''
        if self.door_status == 0:
            log_msg = 'La porte est restee ouverte {} secondes'.format(
                self.duree_ouverture())
            mqtt_msg = 'closed {}'.format(self.duree_ouverture())

            send_mqtt("ouverture", mqtt_msg)
            log_ouverture.warning('%s', log_msg)
            stdout(log_msg)
            mail(log_msg)

        self.door_status = 1  # porte fermee
        self.tick_ouverture = 0
        time.sleep(0.2)
        self.tick_fermeture += 1
        if self.tick_fermeture % 40 == 0:  # fermee depuis 5s
            log_uptime_door.warning('1')
            send_mqtt("statusdoor", 1)


if __name__ == '__main__':
    ###########################################################################
    ################################  setup    ################################
    ###########################################################################

    # CONFIGURATION
    # verbose : affichage console, sinon seulement dans des fichiers log
    verbose = parse_args()

    # GPIO Setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Door instance pour gérer réactions aux capteurs
    door = Door()

    # logging avec rotating log limite a 5 mb
    log_ouverture = setup_app_log(logfile_ouvertures)
    log_errors = setup_app_log(logfile_errors)
    log_uptime_door = setup_app_log(logfile_status)
    log_stdout = setup_app_log(logfile_print)

    # lancement du script
    time.sleep(5)  # pour que la connexion wifi soit établie
    log_ouverture.warning('%s', 'Lancement du script ReedDoor')
    log_stdout.warning("Lancement du script reed door")
    if verbose:
        print("Lancement du script reed door")
    send_mqtt("ouverture", 'lancement')
    mail('Lancement du script ReedDoor')

    ############################################################################
    #############################   GPIO while loop  ###########################
    ############################################################################

    while True:
        # on lit l'état du capteur
        input_state = GPIO.input(18)
        if input_state:
            door.door_closed()
        else:
            door.door_opened()
