#!/usr/bin/env python3
import os
import sys
import logging
import shutil
from flask import Flask, request, jsonify, send_file, render_template
import time
from pathlib import Path
import csv
import pandas as pd
from datetime import datetime
import json
import sqlite3
import io
import paramiko
import base64
import glob

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_FOLDER = os.path.join(BASE_DIR, 'files')  # Dossier contenant les fichiers à servir
LOG_FILE = os.path.join(BASE_DIR, 'macos_installer.log')
SERVER_PORT = 5001
SCAN_RESULTS_FILE = os.path.join(BASE_DIR, 'scan_results.csv')
DB_FILE = os.path.join(BASE_DIR, 'system_info.db')
SYSTEM_INFO_DIR = os.path.join(BASE_DIR, 'system_info')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
APPS_DIR = os.path.join(BASE_DIR, 'apps')  # Dossier contenant les applications

# Configuration SSH
SSH_USERNAME = "vv"
SSH_PASSWORD = "nnn"

# Configuration du logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Créer les dossiers nécessaires
os.makedirs(FILES_FOLDER, exist_ok=True)
os.makedirs(SYSTEM_INFO_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(APPS_DIR, exist_ok=True)

def init_db():
    """Initialise la base de données SQLite"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Création de la table system_info
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            ip TEXT NOT NULL,
            data JSON NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Création d'un index sur hostname
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_hostname ON system_info(hostname)
        ''')
        
        conn.commit()
        conn.close()
        log("INFO", "Base de données initialisée avec succès")
    except Exception as e:
        log("ERROR", f"Erreur lors de l'initialisation de la base de données: {str(e)}")
        raise

def get_db():
    """Retourne une connexion à la base de données"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def log(level, message):
    """Fonction de logging améliorée"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)  # Affiche aussi dans la console
    logging.log(getattr(logging, level), message)

def check_prerequisites():
    """Vérifie les prérequis"""
    try:
        # Vérifier que les dossiers existent
        for folder in [FILES_FOLDER, SYSTEM_INFO_DIR, TEMPLATES_DIR, APPS_DIR]:
            if not os.path.exists(folder):
                log("ERROR", f"Le dossier {folder} n'existe pas")
                return False
            
            if not os.access(folder, os.R_OK):
                log("ERROR", f"Le dossier {folder} n'est pas accessible en lecture")
                return False
            
        return True
    except Exception as e:
        log("ERROR", f"Erreur lors de la vérification des prérequis: {str(e)}")
        return False

def execute_ssh_command(ip, command):
    """Exécute une commande SSH sur une machine distante"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=SSH_USERNAME, password=SSH_PASSWORD, timeout=10)
        
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        ssh.close()
        return output, error
    except Exception as e:
        return None, str(e)

def check_app_installed(ip, app_name):
    """Vérifie si une application est installée sur une machine"""
    try:
        cmd = f"ls /Applications/{app_name}.app 2>/dev/null || echo 'not_found'"
        output, error = execute_ssh_command(ip, cmd)
        return 'not_found' not in output
    except:
        return False

def install_app(ip, app_name):
    """Installe une application sur une machine distante"""
    try:
        app_path = os.path.join(APPS_DIR, f"{app_name}.app")
        if not os.path.exists(app_path):
            return False, f"Application {app_name} non trouvée sur le serveur"

        # Créer un fichier temporaire pour l'application
        temp_file = f"/tmp/{app_name}.app.tar.gz"
        
        # Compresser l'application
        os.system(f"cd {APPS_DIR} && tar -czf {temp_file} {app_name}.app")
        
        # Transférer l'application via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=SSH_USERNAME, password=SSH_PASSWORD)
        
        sftp = ssh.open_sftp()
        remote_temp = f"/tmp/{app_name}.app.tar.gz"
        sftp.put(temp_file, remote_temp)
        
        # Installer l'application
        commands = [
            f"sudo rm -rf /Applications/{app_name}.app",
            f"sudo tar -xzf {remote_temp} -C /Applications",
            f"sudo chown -R root:wheel /Applications/{app_name}.app",
            f"rm {remote_temp}"
        ]
        
        for cmd in commands:
            output, error = execute_ssh_command(ip, cmd)
            if error and 'not found' not in error:
                return False, f"Erreur lors de l'installation: {error}"
        
        # Nettoyer le fichier temporaire local
        os.remove(temp_file)
        
        return True, "Installation réussie"
    except Exception as e:
        return False, f"Erreur lors de l'installation: {str(e)}"

# Routes Flask
@app.route('/')
def index():
    """Page d'accueil avec le tableau des systèmes"""
    return render_template('index.html')

@app.route('/api/systems')
def get_systems_data():
    """API pour récupérer les données des systèmes au format JSON"""
    try:
        systems = []
        for filename in os.listdir(SYSTEM_INFO_DIR):
            if filename.endswith('.json'):
                hostname = filename[:-5]
                file_path = os.path.join(SYSTEM_INFO_DIR, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    system_info = data.get('system_info', {})
                    systems.append({
                        'hostname': hostname,
                        'ip': data.get('ip'),
                        'last_update': data.get('timestamp'),
                        'battery': system_info.get('battery'),
                        'current_user': system_info.get('current_user'),
                        'boot_time': system_info.get('boot_time'),
                        'disk': system_info.get('disk'),
                        'running_apps': system_info.get('running_apps'),
                        'cpu': system_info.get('cpu'),
                        'memory': system_info.get('memory'),
                        'macos_version': system_info.get('macos_version'),
                        'macos_build': system_info.get('macos_build')
                    })
        return jsonify({'data': systems})
    except Exception as e:
        log("ERROR", f"Erreur lors de la récupération des données: {str(e)}")
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

        # Sauvegarder les données dans un fichier JSON
        hostname = data['hostname']
        filename = f"{hostname}.json"
        file_path = os.path.join(SYSTEM_INFO_DIR, filename)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Stocker aussi dans la base de données
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO system_info (hostname, timestamp, ip, data)
            VALUES (?, ?, ?, ?)
            ''', (
                data['hostname'],
                data['timestamp'],
                data['ip'],
                json.dumps(data)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            log("WARNING", f"Erreur lors du stockage dans la base de données: {str(e)}")

        log("INFO", f"Informations système reçues de {hostname} ({data['ip']})")
        return jsonify({'message': 'Informations système reçues avec succès'}), 200

    except Exception as e:
        log("ERROR", f"Erreur lors de la réception des informations système: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/apps', methods=['GET'])
def list_apps():
    """Liste les applications disponibles"""
    try:
        apps = []
        for app in glob.glob(os.path.join(APPS_DIR, "*.app")):
            app_name = os.path.basename(app).replace('.app', '')
            apps.append({
                'name': app_name,
                'size': os.path.getsize(app),
                'modified': datetime.fromtimestamp(os.path.getmtime(app)).strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify({'apps': apps}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/apps/<app_name>/install/<ip>', methods=['POST'])
def install_app_endpoint(app_name, ip):
    """Endpoint pour installer une application sur une machine"""
    try:
        # Vérifier si l'application est déjà installée
        if check_app_installed(ip, app_name):
            return jsonify({'message': 'Application déjà installée'}), 200
        
        # Installer l'application
        success, message = install_app(ip, app_name)
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/apps/<app_name>/status/<ip>', methods=['GET'])
def check_app_status(app_name, ip):
    """Vérifie le statut d'une application sur une machine"""
    try:
        installed = check_app_installed(ip, app_name)
        return jsonify({
            'app_name': app_name,
            'ip': ip,
            'installed': installed
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/csv')
def export_csv():
    """Exporte les données au format CSV"""
    try:
        systems = []
        for filename in os.listdir(SYSTEM_INFO_DIR):
            if filename.endswith('.json'):
                hostname = filename[:-5].split('.')[0]  # tronquer le hostname
                file_path = os.path.join(SYSTEM_INFO_DIR, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    system_info = data.get('system_info', {})
                    battery = system_info.get('battery', {})
                    disk = system_info.get('disk', {})
                    systems.append({
                        'Hostname': hostname,
                        'IP': data.get('ip'),
                        'Last Update': data.get('timestamp'),
                        'macOS Version': system_info.get('macos_version'),
                        'macOS Build': system_info.get('macos_build'),
                        'Battery %': battery.get('percent'),
                        'Battery Max Capacity (%)': battery.get('max_capacity_percent'),
                        'Battery Condition': battery.get('condition'),
                        'Power Plugged': battery.get('power_plugged'),
                        'Battery Time Left': battery.get('time_left'),
                        'Current User': system_info.get('current_user'),
                        'Boot Time': system_info.get('boot_time'),
                        'Disk Total (GB)': disk.get('total'),
                        'Disk Free (GB)': disk.get('free'),
                        'Disk Usage %': disk.get('percent')
                    })
        # Créer le CSV en mémoire
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=systems[0].keys())
        writer.writeheader()
        writer.writerows(systems)
        # Préparer la réponse
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'systems_info_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        log("ERROR", f"Erreur lors de l'export CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/xlsx')
def export_xlsx():
    """Exporte les données au format XLSX"""
    try:
        systems = []
        for filename in os.listdir(SYSTEM_INFO_DIR):
            if filename.endswith('.json'):
                hostname = filename[:-5].split('.')[0]  # tronquer le hostname
                file_path = os.path.join(SYSTEM_INFO_DIR, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    system_info = data.get('system_info', {})
                    battery = system_info.get('battery', {})
                    disk = system_info.get('disk', {})
                    systems.append({
                        'Hostname': hostname,
                        'IP': data.get('ip'),
                        'Last Update': data.get('timestamp'),
                        'macOS Version': system_info.get('macos_version'),
                        'macOS Build': system_info.get('macos_build'),
                        'Battery %': battery.get('percent'),
                        'Battery Max Capacity (%)': battery.get('max_capacity_percent'),
                        'Battery Condition': battery.get('condition'),
                        'Power Plugged': battery.get('power_plugged'),
                        'Battery Time Left': battery.get('time_left'),
                        'Current User': system_info.get('current_user'),
                        'Boot Time': system_info.get('boot_time'),
                        'Disk Total (GB)': disk.get('total'),
                        'Disk Free (GB)': disk.get('free'),
                        'Disk Usage %': disk.get('percent')
                    })
        # Créer le DataFrame et exporter en XLSX
        df = pd.DataFrame(systems)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Systems Info', index=False)
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'systems_info_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        log("ERROR", f"Erreur lors de l'export XLSX: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/xml')
def export_xml():
    """Exporte les données au format XML"""
    try:
        systems = []
        for filename in os.listdir(SYSTEM_INFO_DIR):
            if filename.endswith('.json'):
                hostname = filename[:-5].split('.')[0]  # tronquer le hostname
                file_path = os.path.join(SYSTEM_INFO_DIR, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    system_info = data.get('system_info', {})
                    battery = system_info.get('battery', {})
                    disk = system_info.get('disk', {})
                    systems.append({
                        'Hostname': hostname,
                        'IP': data.get('ip'),
                        'Last Update': data.get('timestamp'),
                        'macOS Version': system_info.get('macos_version'),
                        'macOS Build': system_info.get('macos_build'),
                        'Battery %': battery.get('percent'),
                        'Battery Max Capacity (%)': battery.get('max_capacity_percent'),
                        'Battery Condition': battery.get('condition'),
                        'Power Plugged': battery.get('power_plugged'),
                        'Battery Time Left': battery.get('time_left'),
                        'Current User': system_info.get('current_user'),
                        'Boot Time': system_info.get('boot_time'),
                        'Disk Total (GB)': disk.get('total'),
                        'Disk Free (GB)': disk.get('free'),
                        'Disk Usage %': disk.get('percent')
                    })
        # Créer le DataFrame et exporter en XML
        df = pd.DataFrame(systems)
        output = io.BytesIO()
        df.to_xml(output, index=False, root_name='systems', row_name='system', encoding='utf-8', xml_declaration=True, pretty_print=True)
        output.seek(0)
        return send_file(
            output,
            mimetype='application/xml',
            as_attachment=True,
            download_name=f'systems_info_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml'
        )
    except Exception as e:
        log("ERROR", f"Erreur lors de l'export XML: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/files/<path:filename>')
def serve_file(filename):
    """Sert un fichier depuis le dossier files"""
    try:
        return send_file(os.path.join(FILES_FOLDER, filename))
    except Exception as e:
        log("ERROR", f"Erreur lors de la récupération du fichier {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 404

@app.route('/settings')
def settings():
    """Page de configuration"""
    return render_template('settings.html')

if __name__ == '__main__':
    try:
        # Vérifier les prérequis
        if not check_prerequisites():
            log("ERROR", "Les prérequis ne sont pas satisfaits")
            sys.exit(1)
        
        # Initialiser la base de données
        init_db()
        
        log("INFO", f"Démarrage du serveur sur le port {SERVER_PORT}")
        log("INFO", f"Dossier des fichiers: {FILES_FOLDER}")
        
        # Démarrer le serveur Flask
        app.run(host='0.0.0.0', port=SERVER_PORT)
    except Exception as e:
        log("ERROR", f"Erreur lors du démarrage du serveur: {str(e)}")
        sys.exit(1)