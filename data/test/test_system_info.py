#!/usr/bin/env python3
import psutil
import platform
import os
from datetime import datetime
import subprocess

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

def get_current_user():
    """Récupère l'utilisateur actuel"""
    return os.getlogin()

def get_running_apps():
    """Récupère les applications en cours d'exécution"""
    # Utiliser osascript pour obtenir la liste des applications actives
    try:
        cmd = '''osascript -e 'tell application "System Events" to get name of every process where background only is false' '''
        output = subprocess.check_output(cmd, shell=True).decode('utf-8')
        app_names = [name.strip() for name in output.split(', ')]
        
        apps_info = {}
        for app_name in app_names:
            if app_name:
                # Trouver tous les PIDs pour cette application
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
        print(f"Erreur lors de la récupération des applications : {str(e)}")
        return {}

def get_system_resources():
    """Récupère les ressources système"""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    
    # Mémoire
    memory = psutil.virtual_memory()
    
    # Disque
    disk = psutil.disk_usage('/')
    
    return {
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
        }
    }

def main():
    print("\n=== Informations Système ===\n")
    
    # Utilisateur actuel
    current_user = get_current_user()
    print(f"Utilisateur actuel : {current_user}")
    
    # Batterie
    battery_info = get_battery_info()
    if battery_info:
        print("\n=== Informations Batterie ===")
        print(f"Niveau de batterie : {battery_info['percent']}%")
        print(f"Alimentation secteur : {'Oui' if battery_info['power_plugged'] else 'Non'}")
        if battery_info['time_left'] != "Charging":
            print(f"Temps restant : {battery_info['time_left'] // 3600}h {(battery_info['time_left'] % 3600) // 60}m")
    
    # Ressources système
    resources = get_system_resources()
    print("\n=== Ressources Système ===")
    print(f"CPU : {resources['cpu']['percent']}% ({resources['cpu']['count']} cœurs)")
    print(f"Mémoire : {resources['memory']['percent']}% utilisée ({resources['memory']['available']} GB disponible)")
    print(f"Disque : {resources['disk']['percent']}% utilisé ({resources['disk']['free']} GB libre)")
    
    # Applications en cours
    print("\n=== Applications en cours d'exécution ===")
    apps = get_running_apps()
    for app_name, info in apps.items():
        print(f"\nApplication : {app_name}")
        print(f"  PIDs : {', '.join(map(str, info['pids']))}")
        print(f"  CPU total : {info['cpu_percent']}%")
        print(f"  Mémoire totale : {info['memory_percent']}%")

if __name__ == "__main__":
    main() 