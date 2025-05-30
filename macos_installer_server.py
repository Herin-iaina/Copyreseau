#!/usr/bin/env python3
import os
import sys
import logging
import shutil
from flask import Flask, request, jsonify, send_file
import time
from pathlib import Path
import csv
import pandas as pd
from datetime import datetime
import json

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_FOLDER = os.path.join(BASE_DIR, 'files')  # Dossier contenant les fichiers à servir
LOG_FILE = os.path.join(BASE_DIR, 'macos_installer.log')
SERVER_PORT = 5001
SCAN_RESULTS_FILE = os.path.join(BASE_DIR, 'scan_results.csv')
SYSTEM_INFO_DIR = os.path.join(BASE_DIR, 'data')

# Configuration du logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

def log(level, message):
    """Fonction de logging améliorée"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)  # Affiche aussi dans la console
    logging.log(getattr(logging, level), message)

def check_prerequisites():
    """Vérifie les prérequis"""
    try:
        # Vérifier que le dossier files existe
        if not os.path.exists(FILES_FOLDER):
            log("ERROR", f"Le dossier {FILES_FOLDER} n'existe pas")
            return False
            
        # Vérifier les permissions du dossier
        if not os.access(FILES_FOLDER, os.R_OK):
            log("ERROR", f"Le dossier {FILES_FOLDER} n'est pas accessible en lecture")
            return False
            
        return True
    except Exception as e:
        log("ERROR", f"Erreur lors de la vérification des prérequis: {str(e)}")
        return False

def update_scan_results(hostname, ip):
    """Met à jour le fichier CSV des résultats de scan"""
    try:
        # Créer le fichier s'il n'existe pas
        if not os.path.exists(SCAN_RESULTS_FILE):
            with open(SCAN_RESULTS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['IP Address', 'MAC Address', 'Hostname', 'Client Reported', 'Last Update'])
        
        # Lire le fichier existant
        df = pd.read_csv(SCAN_RESULTS_FILE)
        
        # Vérifier si l'hôte existe déjà
        hostname_exists = df['Hostname'].str.upper() == hostname.upper()
        
        if hostname_exists.any():
            # Mettre à jour l'entrée existante
            df.loc[hostname_exists, ['IP Address', 'Client Reported', 'Last Update']] = [
                ip, True, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
        else:
            # Ajouter une nouvelle entrée
            new_row = {
                'IP Address': ip,
                'MAC Address': 'Unknown',
                'Hostname': hostname,
                'Client Reported': True,
                'Last Update': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Sauvegarder les modifications
        df.to_csv(SCAN_RESULTS_FILE, index=False)
        log("INFO", f"Mise à jour réussie pour {hostname} ({ip})")
        return True
    except Exception as e:
        log("ERROR", f"Erreur lors de la mise à jour du fichier CSV: {str(e)}")
        return False

@app.route('/files', methods=['GET'])
def list_files():
    """Liste les fichiers disponibles"""
    try:
        files = []
        for file in os.listdir(FILES_FOLDER):
            file_path = os.path.join(FILES_FOLDER, file)
            if os.path.isfile(file_path):
                files.append({
                    'name': file,
                    'size': os.path.getsize(file_path),
                    'modified': os.path.getmtime(file_path)
                })
        return jsonify({'files': files}), 200
    except Exception as e:
        log("ERROR", f"Erreur lors de la liste des fichiers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    """Sert un fichier spécifique"""
    try:
        file_path = os.path.join(FILES_FOLDER, filename)
        if not os.path.exists(file_path):
            log("ERROR", f"Fichier non trouvé: {filename}")
            return jsonify({'error': 'Fichier non trouvé'}), 404
            
        log("INFO", f"Envoi du fichier: {filename}")
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        log("ERROR", f"Erreur lors de l'envoi du fichier: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Retourne le statut du serveur"""
    try:
        with open(LOG_FILE, 'r') as f:
            logs = f.readlines()[-50:]  # Dernières 50 lignes
        return jsonify({'status': 'running', 'logs': logs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/report', methods=['POST'])
def report_client_info():
    """Reçoit les informations du client et met à jour le fichier CSV"""
    try:
        data = request.get_json()
        if not data or 'hostname' not in data or 'ip' not in data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        hostname = data['hostname']
        ip = data['ip']
        
        if update_scan_results(hostname, ip):
            return jsonify({'message': 'Informations mises à jour avec succès'}), 200
        else:
            return jsonify({'error': 'Erreur lors de la mise à jour'}), 500
            
    except Exception as e:
        log("ERROR", f"Erreur lors de la réception des informations client: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/system_info', methods=['POST'])
def receive_system_info():
    """Reçoit les informations système du client"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Aucune donnée reçue'}), 400

        # Vérifier les champs obligatoires
        required_fields = ['timestamp', 'hostname', 'ip', 'system_info']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Champ manquant: {field}'}), 400

        # Créer le dossier data s'il n'existe pas
        data_dir = os.path.join(BASE_DIR, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Sauvegarder les données dans un fichier JSON
        hostname = data['hostname']
        timestamp = data['timestamp'].replace(':', '-').replace(' ', '_')
        filename = f"system_info_{hostname}_{timestamp}.json"
        file_path = os.path.join(data_dir, filename)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        log("INFO", f"Informations système reçues de {hostname} ({data['ip']})")
        return jsonify({'message': 'Informations système reçues avec succès'}), 200

    except Exception as e:
        log("ERROR", f"Erreur lors de la réception des informations système: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/system_info/<hostname>', methods=['GET'])
def get_system_info(hostname):
    """Récupère les informations système d'un hôte spécifique"""
    try:
        file_path = os.path.join(SYSTEM_INFO_DIR, f"{hostname}.json")
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Extraire les informations spécifiques
            system_info = data.get('system_info', {})
            response = {
                'hostname': data.get('hostname'),
                'ip': data.get('ip'),
                'timestamp': data.get('timestamp'),
                'battery': system_info.get('battery', {}),
                'current_user': system_info.get('current_user'),
                'boot_time': system_info.get('boot_time'),
                'disk': system_info.get('disk', {})
            }
            return jsonify(response), 200
        else:
            return jsonify({'error': 'Aucune information trouvée pour cet hôte'}), 404
            
    except Exception as e:
        log("ERROR", f"Erreur lors de la récupération des informations système: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/system_info', methods=['GET'])
def list_all_systems():
    """Liste toutes les machines surveillées avec leurs informations système"""
    try:
        systems = []
        for filename in os.listdir(SYSTEM_INFO_DIR):
            if filename.endswith('.json'):
                hostname = filename[:-5]  # Enlever l'extension .json
                file_path = os.path.join(SYSTEM_INFO_DIR, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    system_info = data.get('system_info', {})
                    systems.append({
                        'hostname': hostname,
                        'ip': data.get('ip'),
                        'last_update': data.get('timestamp'),
                        'battery': system_info.get('battery', {}),
                        'current_user': system_info.get('current_user'),
                        'boot_time': system_info.get('boot_time'),
                        'disk': system_info.get('disk', {})
                    })
        return jsonify({'systems': systems}), 200
    except Exception as e:
        log("ERROR", f"Erreur lors de la liste des systèmes: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        # Vérifier les prérequis
        if not check_prerequisites():
            log("ERROR", "Les prérequis ne sont pas satisfaits")
            sys.exit(1)
        
        log("INFO", f"Démarrage du serveur sur le port {SERVER_PORT}")
        log("INFO", f"Dossier des fichiers: {FILES_FOLDER}")
        
        # Démarrer le serveur Flask
        app.run(host='0.0.0.0', port=SERVER_PORT)
    except Exception as e:
        log("ERROR", f"Erreur lors du démarrage du serveur: {str(e)}")
        sys.exit(1) 