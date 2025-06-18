# Smartelia - Plateforme de gestion et de déploiement réseau

## Table des matières
- [Présentation](#présentation)
- [Prérequis](#prérequis)
- [Installation et utilisation](#installation-et-utilisation)
- [Structure du projet](#structure-du-projet)
- [Fonctionnalités principales](#fonctionnalités-principales)
- [Utilisation en conteneur Docker](#utilisation-en-conteneur-docker)
- [Construction et installation du client macOS](#construction-et-installation-du-client-macos)
- [Tests](#tests)
- [Désinstallation](#désinstallation)
- [Dépannage](#dépannage)

---

## Présentation

Ce projet propose :
- Un serveur Flask pour la gestion centralisée des informations systèmes des clients macOS, l'installation d'applications à distance, l'export de données, etc.
- Un client macOS (installable via un package) qui remonte les informations système.
- Des outils de scan réseau et de tests.

---

## Prérequis

- Python 3.6 ou supérieur (recommandé : 3.9+)
- Nmap installé (`brew install nmap` sur macOS)
- Xcode (pour la construction du package client)
- Docker (optionnel, pour l'utilisation en conteneur)
- Accès administrateur pour certaines opérations

---

## Installation et utilisation

### 1. Installation des dépendances Python

Créez et activez un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/macOS
# ou
.\venv\Scripts\activate  # Sur Windows
```
Installez les dépendances :
```bash
pip install -r requirements.txt
```

### 2. Lancement du serveur Flask

```bash
python macos_installer_server.py
```
Le serveur sera accessible sur le port 5001.

### 3. Accès à l'interface web

- Page d'accueil : http://localhost:5001/
- Page de configuration : http://localhost:5001/settings
  - Cette page propose un bouton permettant de réinitialiser toutes les données du serveur (infos systèmes, logs, etc.).
  - Le bouton envoie une requête POST à `/reset_data` (à implémenter côté serveur).

---

## Structure du projet

- `macos_installer_server.py` : serveur principal Flask (API, gestion des apps, export, etc.)
- `network_scanner.py` : script de scan réseau
- `host_client.py` : client à déployer sur les machines macOS
- `templates/` : templates HTML (ex : `index.html`, `settings.html`)
- `apps/` : applications à déployer sur les clients
- `data/` : dossiers pour les fichiers, infos systèmes, logs, etc.
- `output/` : contient le package d'installation généré (`SmarteliaClient-1.0.pkg`)
- `ipscan/` : environnement virtuel Python embarqué (librairies, binaires)
- `build_package.sh` : script de construction du package d'installation macOS
- `manual_uninstall.txt` : instructions de désinstallation manuelle
- `com.smartelia.hostclient.plist` : fichier de configuration du service macOS

---

## Fonctionnalités principales

- **Collecte d'informations système** (POST `/system_info`)
- **Tableau de bord web** (GET `/`)
- **Export CSV/XLSX/XML** (GET `/export/csv`, `/export/xlsx`, `/export/xml`)
- **Gestion des applications** (liste, installation à distance, statut)
- **API de fichiers** (GET `/files`)
- **Page de configuration** (GET `/settings`)
  - Avec bouton de réinitialisation des données (POST `/reset_data`)
- **Scan réseau** (`network_scanner.py`)
- **Tests automatisés** (`data/test/`)

---

## Utilisation en conteneur Docker

### Construction de l'image

```bash
docker build --network=host -t macos-installer .
```

### Lancement du conteneur

```bash
docker run -d \
  --name macos-installer \
  --network host \
  -v "$(pwd)/data/files:/data/files" \
  -v "$(pwd)/data/system_info:/data/system_info" \
  -v "$(pwd)/data/templates:/data/templates" \
  -v "$(pwd)/data/apps:/data/apps" \
  -v "$(pwd)/data/macos_installer.log:/data/macos_installer.log" \
  -v "$(pwd)/data/system_info.db:/data/system_info.db" \
  -v "$(pwd)/data/scan_results.csv:/data/scan_results.csv" \
  --restart unless-stopped \
  macos-installer
```

---

## Construction et installation du client macOS

Voir `README_PACKAGE.txt` pour le détail complet.

Résumé :
- Rendez exécutable `build_package.sh` puis lancez-le pour générer le package dans `output/`.
- Installez le package sur le client macOS (double-clic sur `SmarteliaClient-1.0.pkg`).

---

## Tests

Des scripts de test sont disponibles dans `data/test/` :
- `test_system_info.py`
- `test_system_info.sh`

---

## Désinstallation

Voir `manual_uninstall.txt` pour la désinstallation manuelle du client.

---

## Dépannage

Consultez les logs, vérifiez les services, et reportez-vous à la section "Dépannage" de `README_PACKAGE.txt`.
