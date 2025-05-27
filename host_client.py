#!/usr/bin/env python3
import socket
import requests
import platform
import time
import sys
import logging
from pathlib import Path

# Configuration
SERVER_URL = "http://localhost:5001"  # URL du serveur
LOG_FILE = "host_client.log"

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

def main():
    log("INFO", "Démarrage du client")
    
    # Essayer d'envoyer les informations
    if send_info_to_server():
        log("INFO", "Opération terminée avec succès")
    else:
        log("ERROR", "Échec de l'opération")
        sys.exit(1)

if __name__ == "__main__":
    main() 