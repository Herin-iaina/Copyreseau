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

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_FOLDER = os.path.join(BASE_DIR, 'files')  # Dossier contenant les fichiers à servir
LOG_FILE = os.path.join(BASE_DIR, 'macos_installer.log')
SERVER_PORT = 5001
SCAN_RESULTS_FILE = os.path.join(BASE_DIR, 'scan_results.csv')

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