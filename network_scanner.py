#!/usr/bin/env python3
import socket
import subprocess
import platform
import concurrent.futures
from datetime import datetime
from tqdm import tqdm
import paramiko
import re
import time
import csv
import os
import glob

# Configuration SSH
USE_SSH = True  # Mettre à False pour désactiver SSH
SSH_USERNAME = "smartelia"  # Remplacer par votre nom d'utilisateur
SSH_PASSWORD = "WeAr24DM!n"  # Remplacer par votre mot de passe

# Configuration des applications macOS
APPLICATIONS_TO_CHECK = [
    "MonApplication.app",
    "AutreApplication.app",
    # Ajoutez ici les noms des applications à vérifier
]

# Chemins des applications sur macOS
APPLICATIONS_PATH = "Applications"  # Chemin relatif
FILES_PATH = "/Users/smartelia/files"  # Chemin sur le serveur

macbook_pro_models = {
    "Mac16,6": ("14 pouces", 2024),
    "Mac16,8": ("14 pouces", 2024),
    "Mac16,7": ("16 pouces", 2024),
    "Mac16,5": ("16 pouces", 2024),
    "Mac15,3": ("14 pouces", 2023),
    "Mac15,6": ("14 pouces", 2023),
    "Mac16,1": ("14 pouces", 2024),
    "Mac16,6": ("14 pouces", 2024),
    "Mac16,8": ("14 pouces", 2024),
    "Mac16,7": ("16 pouces", 2024),
    "Mac16,5": ("16 pouces", 2024),
    "Mac15,3": ("14 pouces", 2023),
    "Mac15,6": ("14 pouces", 2023),
    "Mac15,8": ("14 pouces", 2023),
    "Mac15,10":("14 pouces", 2023),
    "Mac15,7": ("16 pouces", 2023),
    "Mac15,9": ("16 pouces", 2023),
    "Mac15,11":("16 pouces", 2023),
    "Mac14,5": ("14 pouces", 2023),
    "Mac14,9": ("14 pouces", 2023),
    "Mac14,6": ("16 pouces", 2023),
    "Mac14,10":("16 pouces", 2023),
    "Mac14,7": ("13 pouces", 2022),
    "MacBookPro18,3":("14 pouces", 2021),
    "MacBookPro18,4":("14 pouces", 2021),
    "MacBookPro18,1":("16 pouces", 2021),
    "MacBookPro18,2":("16 pouces", 2021),
    "MacBookPro17,1":("13 pouces", 2020),
    "MacBookPro16,3":("13 pouces", 2020),
    "MacBookPro16,2":("13 pouces", 2020),
    "MacBookPro16,1":("16 pouces", 2019),
    "MacBookPro16,4":("16 pouces", 2019),
    "MacBookPro12,1": ("13 pouces", 2015),
    "MacBookPro14,2": ("13 pouces", 2017),
}

def ping(ip):
    """Ping an IP address and return True if it responds"""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout = '-W' if platform.system().lower() != 'windows' else '-w'
    timeout_value = '1' if platform.system().lower() != 'windows' else '1000'
    command = ['ping', param, '1', timeout, timeout_value, ip]
    return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def get_mac_address(ip):
    """Get MAC address using arp command"""
    try:
        # Exécuter la commande arp
        if platform.system().lower() == 'windows':
            output = subprocess.check_output(f'arp -a {ip}', shell=True).decode()
        else:
            output = subprocess.check_output(f'arp -n {ip}', shell=True).decode()
        
        # Extraire l'adresse MAC
        mac_pattern = r'([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})'
        match = re.search(mac_pattern, output)
        if match:
            return match.group(1)
    except:
        pass
    return "Unknown"

def check_and_install_application(ssh, application_name):
    """Vérifie si l'application existe sur macOS et l'installe si nécessaire"""
    # try:
    #     # Vérifier si l'application existe dans le dossier Applications
    #     check_cmd = f'ls ~/{APPLICATIONS_PATH}/{application_name}'
    #     
    #     stdin, stdout, stderr = ssh.exec_command(check_cmd)
    #     if stdout.channel.recv_exit_status() == 0:
    #         # L'application existe, on vérifie si une mise à jour est nécessaire
    #         print(f"Mise à jour de {application_name} sur {ssh.get_transport().getpeername()[0]}")
    #         # Commande pour mettre à jour l'application
    #         update_cmd = f'cd {FILES_PATH} && ./update_{application_name}'
    #         ssh.exec_command(update_cmd)
    #     else:
    #         # L'application n'existe pas, on l'installe
    #         print(f"Installation de {application_name} sur {ssh.get_transport().getpeername()[0]}")
    #         
    #         # Créer le dossier Applications s'il n'existe pas
    #         ssh.exec_command(f'mkdir -p ~/{APPLICATIONS_PATH}')
    #         
    #         # Copier l'application depuis le serveur vers le client
    #         copy_cmd = f'scp -r {FILES_PATH}/{application_name} ~/{APPLICATIONS_PATH}/'
    #         ssh.exec_command(copy_cmd)
    #         
    #         # Vérifier si l'installation a réussi
    #         time.sleep(5)  # Attendre un peu pour l'installation
    #         stdin, stdout, stderr = ssh.exec_command(check_cmd)
    #         if stdout.channel.recv_exit_status() == 0:
    #             print(f"Installation de {application_name} réussie")
    #         else:
    #             print(f"Échec de l'installation de {application_name}")
    # except Exception as e:
    #     print(f"Erreur lors de la vérification/installation de {application_name}: {str(e)}")

def try_ssh_connection(ip, username, password):
    """Try to connect via SSH and get hostname, model info, and macOS version"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=5)
        
        # Exécuter la commande hostname
        stdin, stdout, stderr = ssh.exec_command('hostname')
        hostname = stdout.read().decode().strip()

        # Récupérer le Model Name et Model Identifier
        stdin, stdout, stderr = ssh.exec_command('system_profiler SPHardwareDataType | grep "Model Name\\|Model Identifier"')
        model_info = stdout.read().decode().replace('\n', ' ').strip()

        # Récupérer la version de macOS
        stdin, stdout, stderr = ssh.exec_command('sw_vers -productVersion')
        macos_version = stdout.read().decode().strip()
        
        ssh.close()
        return {
            'hostname': hostname if hostname else "Unknown",
            'model_info': model_info if model_info else "Unknown",
            'macos_version': macos_version if macos_version else "Unknown"
        }
    except:
        return {
            'hostname': "Unknown",
            'model_info': "Unknown",
            'macos_version': "Unknown"
        }

def extract_model_identifier(model_info):
    match = re.search(r'(Mac(?:BookPro)?[0-9,]+|Mac[0-9,]+)', model_info)
    if match:
        return match.group(1)
    return "Unknown"

def scan_ip(ip, ssh_credentials=None):
    """Scan a single IP address"""
    try:
        if ping(ip):
            mac = get_mac_address(ip)
            hostname = "Unknown"
            model_info = "Unknown"
            macos_version = "Unknown"
            model_identifier = "Unknown"
            taille = "Unknown"
            annee = "Unknown"
            
            # Si SSH est activé, essayer la connexion SSH
            if USE_SSH and ssh_credentials:
                ssh_result = try_ssh_connection(ip, ssh_credentials['username'], ssh_credentials['password'])
                if isinstance(ssh_result, dict):
                    hostname = ssh_result.get('hostname', 'Unknown')
                    model_info = ssh_result.get('model_info', 'Unknown')
                    macos_version = ssh_result.get('macos_version', 'Unknown')
                    model_identifier = extract_model_identifier(model_info)
                    taille, annee = macbook_pro_models.get(model_identifier, ("Unknown", "Unknown"))
                else:
                    hostname = ssh_result
            
            return {
                'ip': ip,
                'mac': mac if mac else "Unknown",
                'hostname': hostname if hostname else "Unknown",
                'model_info': model_info if model_info else "Unknown",
                'macos_version': macos_version if macos_version else "Unknown",
                'model_identifier': model_identifier,
                'taille': taille,
                'annee': annee
            }
    except:
        pass
    return None

def save_to_csv(results, filename):
    """Save results to CSV file"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'IP Address', 'MAC Address', 'Hostname', 'Model Info', 'macOS Version',
                'Model Identifier', 'Taille', 'Annee'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                if result:  # Vérifier que le résultat n'est pas None
                    writer.writerow({
                        'IP Address': result.get('ip', 'Unknown'),
                        'MAC Address': result.get('mac', 'Unknown'),
                        'Hostname': result.get('hostname', 'Unknown'),
                        'Model Info': result.get('model_info', 'Unknown'),
                        'macOS Version': result.get('macos_version', 'Unknown'),
                        'Model Identifier': result.get('model_identifier', 'Unknown'),
                        'Taille': result.get('taille', 'Unknown'),
                        'Annee': result.get('annee', 'Unknown')
                    })
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier CSV: {str(e)}")

def is_smartelia_machine(hostname):
    """Vérifie si le nom d'hôte contient 'SMARTELIA' (insensible à la casse)"""
    return hostname and "SMARTELIA" in hostname.upper()

def cleanup_old_csv():
    """Supprime tous les anciens fichiers CSV"""
    try:
        for csv_file in glob.glob("smartelia_machines_*.csv"):
            os.remove(csv_file)
    except:
        pass

def main():
    print("Démarrage du scan réseau...")
    print("Scan des plages d'IP : 172.17.17.0/24 à 172.17.20.0/24")

    # Nettoyer les anciens fichiers CSV
    cleanup_old_csv()

    # Configuration SSH
    ssh_credentials = None
    if USE_SSH:
        ssh_credentials = {
            'username': SSH_USERNAME,
            'password': SSH_PASSWORD
        }

    # Liste des IPs à scanner
    ips_to_scan = []
    for x in range(17, 21):  # 17 à 20
        for y in range(1, 256):  # 1 à 255
            ips_to_scan.append(f"172.17.{x}.{y}")

    # Utiliser ThreadPoolExecutor pour scanner en parallèle avec plus de workers
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        # Créer une barre de progression
        with tqdm(total=len(ips_to_scan), desc="Scanning", unit="IP") as pbar:
            # Scanner les IPs et mettre à jour la barre de progression
            futures = {executor.submit(scan_ip, ip, ssh_credentials): ip for ip in ips_to_scan}
            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)
                try:
                    result = future.result()
                    if result and is_smartelia_machine(result.get('hostname', '')):
                        results.append(result)
                except:
                    pass

    # Sauvegarder les résultats dans un fichier CSV
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"smartelia_machines_{timestamp}.csv"
        save_to_csv(results, filename)
        print(f"\nNombre de machines SMARTELIA trouvées : {len(results)}")
    else:
        print("\nAucune machine SMARTELIA trouvée")

if __name__ == "__main__":
    main() 