#!/usr/bin/env python3
import socket
import requests
import platform
import time
import sys
import logging
import os
import daemon
import signal
from pathlib import Path

# Configuration
SERVER_URL = "http://localhost:5001"  # URL du serveur
LOG_FILE = "/var/log/host_client.log"
PID_FILE = "/var/run/host_client.pid"
CHECK_INTERVAL = 3600  # 1 heure en secondes

# Configuration du logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log(level, message):
    """Fonction de logging améliorée"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)  # Affiche aussi dans la console
    logging.log(getattr(logging, level), message)

def get_hostname():
    """Récupère le nom d'hôte de la machine"""
    try:
        return socket.gethostname()
    except:
        return "Unknown"

def get_ip():
    """Récupère l'adresse IP de la machine"""
    try:
        # Créer une socket pour déterminer l'interface réseau par défaut
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

def send_info_to_server():
    """Envoie les informations au serveur"""
    try:
        hostname = get_hostname()
        ip = get_ip()
        
        if hostname == "Unknown" or ip == "Unknown":
            log("ERROR", "Impossible de récupérer le nom d'hôte ou l'adresse IP")
            return False
        
        # Préparer les données
        data = {
            'hostname': hostname,
            'ip': ip
        }
        
        # Envoyer les données au serveur
        response = requests.post(f"{SERVER_URL}/report", json=data)
        
        if response.status_code == 200:
            log("INFO", f"Informations envoyées avec succès: {hostname} ({ip})")
            return True
        else:
            log("ERROR", f"Erreur lors de l'envoi des informations: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        log("ERROR", "Impossible de se connecter au serveur")
        return False
    except Exception as e:
        log("ERROR", f"Erreur inattendue: {str(e)}")
        return False

def write_pid_file():
    """Écrit le PID dans le fichier PID"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log("ERROR", f"Erreur lors de l'écriture du fichier PID: {str(e)}")

def remove_pid_file():
    """Supprime le fichier PID"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        log("ERROR", f"Erreur lors de la suppression du fichier PID: {str(e)}")

def signal_handler(signum, frame):
    """Gestionnaire de signaux pour arrêter proprement le daemon"""
    log("INFO", "Arrêt du daemon...")
    remove_pid_file()
    sys.exit(0)

def run_daemon():
    """Fonction principale du daemon"""
    # Configuration du daemon
    context = daemon.DaemonContext(
        working_directory='/',
        umask=0o002,
        pidfile=None,  # On gère nous-mêmes le fichier PID
        signal_map={
            signal.SIGTERM: signal_handler,
            signal.SIGINT: signal_handler,
        }
    )
    
    with context:
        write_pid_file()
        log("INFO", "Démarrage du daemon")
        
        while True:
            try:
                send_info_to_server()
            except Exception as e:
                log("ERROR", f"Erreur lors de l'envoi des informations: {str(e)}")
            
            time.sleep(CHECK_INTERVAL)

def main():
    # Vérifier si le daemon est déjà en cours d'exécution
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Vérifier si le processus existe toujours
            try:
                os.kill(pid, 0)
                log("ERROR", f"Le daemon est déjà en cours d'exécution (PID: {pid})")
                sys.exit(1)
            except OSError:
                # Le processus n'existe plus, on peut supprimer le fichier PID
                remove_pid_file()
        except:
            remove_pid_file()
    
    run_daemon()

if __name__ == "__main__":
    main() 