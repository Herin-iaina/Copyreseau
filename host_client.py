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
import psutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Configuration
SERVER_URL = "http://localhost:5001"  # URL du serveur
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
LOG_FILE = os.path.join(LOG_DIR, "host_client.log")
PID_FILE = os.path.join(PROJECT_DIR, "host_client.pid")
SYSTEM_INFO_FILE = os.path.join(DATA_DIR, "system_info.json")
CHECK_INTERVAL = 3600  # 1 heure en secondes

print(f"Chemin du projet : {PROJECT_DIR}")
print(f"Chemin des logs : {LOG_DIR}")
print(f"Chemin des données : {DATA_DIR}")

# Création des répertoires nécessaires
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Répertoires créés : {LOG_DIR}, {DATA_DIR}")
except Exception as e:
    print(f"Erreur lors de la création des répertoires : {str(e)}")
    sys.exit(1)

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

def save_json_file(file_path, data):
    """Sauvegarde les données dans un fichier JSON"""
    try:
        print(f"Tentative de sauvegarde dans : {file_path}")
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Fichier JSON créé/mis à jour : {file_path}")
        log("INFO", f"Fichier JSON créé/mis à jour : {file_path}")
        return True
    except Exception as e:
        error_msg = f"Erreur lors de la sauvegarde du fichier JSON {file_path}: {str(e)}"
        print(error_msg)
        log("ERROR", error_msg)
        return False

def create_initial_system_info():
    """Crée le fichier system_info.json initial"""
    initial_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'hostname': get_hostname(),
        'ip': get_ip(),
        'status': 'initial'
    }
    return save_json_file(SYSTEM_INFO_FILE, initial_data)

def get_hostname():
    """Récupère le nom d'hôte de la machine"""
    try:
        return socket.gethostname()
    except:
        return "Unknown"

def get_ip():
    """Récupère l'adresse IP de la machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

def get_battery_info():
    """Récupère les informations sur la batterie"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            return {
                'percent': battery.percent,
                'power_plugged': battery.power_plugged,
                'time_left': battery.secsleft if battery.secsleft != -2 else "Charging"
            }
        return None
    except:
        return None

def get_running_apps():
    """Récupère les applications en cours d'exécution"""
    try:
        cmd = '''osascript -e 'tell application "System Events" to get name of every process where background only is false' '''
        output = subprocess.check_output(cmd, shell=True).decode('utf-8')
        app_names = [name.strip() for name in output.split(', ')]
        
        apps_info = {}
        for app_name in app_names:
            if app_name:
                pids = []
                total_cpu = 0
                total_mem = 0
                
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        if proc.info['name'] and app_name.lower() in proc.info['name'].lower():
                            pids.append(proc.info['pid'])
                            total_cpu += proc.info['cpu_percent']
                            total_mem += proc.info['memory_percent']
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                if pids:
                    apps_info[app_name] = {
                        'pids': pids,
                        'cpu_percent': round(total_cpu, 2),
                        'memory_percent': round(total_mem, 2)
                    }
        
        return apps_info
    except Exception as e:
        log("ERROR", f"Erreur lors de la récupération des applications : {str(e)}")
        return {}

def get_current_user():
    """Récupère l'utilisateur actuel"""
    try:
        # Utiliser la même approche que le script shell
        cmd = "whoami"
        return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
    except Exception as e:
        log("ERROR", f"Erreur lors de la récupération de l'utilisateur : {str(e)}")
        return "Unknown"

def get_system_info():
    """Récupère les informations système"""
    try:
        print("Récupération des informations système...")
        
        # Informations de base
        hostname = get_hostname()
        ip = get_ip()
        current_user = get_current_user()
        
        # Informations CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Informations mémoire
        memory = psutil.virtual_memory()
        
        # Informations disque
        disk = psutil.disk_usage('/')
        
        # Informations batterie
        battery_info = get_battery_info()
        
        # Applications en cours d'exécution
        running_apps = get_running_apps()
        
        # Informations système
        boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
        
        # Informations réseau
        net_io = psutil.net_io_counters()
        
        system_info = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hostname': hostname,
            'ip': ip,
            'system_info': {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': {
                        'current': round(cpu_freq.current, 2) if cpu_freq else None,
                        'min': round(cpu_freq.min, 2) if cpu_freq else None,
                        'max': round(cpu_freq.max, 2) if cpu_freq else None
                    }
                },
                'memory': {
                    'total': round(memory.total / (1024**3), 2),  # GB
                    'available': round(memory.available / (1024**3), 2),  # GB
                    'percent': memory.percent
                },
                'disk': {
                    'total': round(disk.total / (1024**3), 2),  # GB
                    'used': round(disk.used / (1024**3), 2),  # GB
                    'free': round(disk.free / (1024**3), 2),  # GB
                    'percent': disk.percent
                },
                'battery': battery_info,
                'current_user': current_user,
                'running_apps': running_apps,
                'boot_time': boot_time,
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            }
        }
        
        print("Informations système récupérées avec succès")
        
        # Sauvegarder les informations dans un fichier JSON
        if not save_json_file(SYSTEM_INFO_FILE, system_info):
            print("Erreur lors de la sauvegarde des informations système")
            return None
            
        return system_info
    except Exception as e:
        error_msg = f"Erreur lors de la récupération des informations système: {str(e)}"
        print(error_msg)
        log("ERROR", error_msg)
        return None

def send_info_to_server():
    """Envoie les informations au serveur"""
    try:
        system_info = get_system_info()
        
        if not system_info:
            log("ERROR", "Impossible de récupérer les informations système")
            return False
        
        # Envoyer les données système au serveur
        system_response = requests.post(f"{SERVER_URL}/system_info", json=system_info)
        
        if system_response.status_code != 200:
            log("ERROR", f"Erreur lors de l'envoi des informations système: {system_response.text}")
            return False
            
        # Envoyer les informations de base au serveur (pour la compatibilité)
        basic_info = {
            'hostname': system_info['hostname'],
            'ip': system_info['ip']
        }
        basic_response = requests.post(f"{SERVER_URL}/report", json=basic_info)
        
        if basic_response.status_code == 200:
            log("INFO", f"Informations envoyées avec succès: {system_info['hostname']} ({system_info['ip']})")
            return True
        else:
            log("ERROR", f"Erreur lors de l'envoi des informations de base: {basic_response.text}")
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
        pid_info = {
            'pid': os.getpid(),
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hostname': get_hostname(),
            'ip': get_ip()
        }
        if not save_json_file(PID_FILE, pid_info):
            log("ERROR", "Impossible de créer le fichier PID")
            sys.exit(1)
    except Exception as e:
        log("ERROR", f"Erreur lors de l'écriture du fichier PID: {str(e)}")
        sys.exit(1)

def remove_pid_file():
    """Supprime le fichier PID"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            log("INFO", f"Fichier PID supprimé : {PID_FILE}")
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
        working_directory=PROJECT_DIR,
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
        
        # Forcer une mise à jour complète des informations système
        print("Mise à jour initiale des informations système...")
        system_info = get_system_info()
        if not system_info:
            log("ERROR", "Impossible de récupérer les informations système initiales")
            sys.exit(1)
        
        # Envoyer les informations au serveur immédiatement
        print("Envoi initial des informations au serveur...")
        if not send_info_to_server():
            log("ERROR", "Échec de l'envoi initial des informations")
            sys.exit(1)
        
        while True:
            try:
                send_info_to_server()
            except Exception as e:
                log("ERROR", f"Erreur lors de l'envoi des informations: {str(e)}")
            
            time.sleep(CHECK_INTERVAL)

def main():
    print("Démarrage du script...")
    
    # Vérifier si le daemon est déjà en cours d'exécution
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid_info = json.load(f)
                pid = pid_info['pid']
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