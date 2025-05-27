# Network Scanner

Ce script permet de scanner les machines connectées sur le même réseau et d'obtenir leurs noms d'hôtes.

## Prérequis

- Python 3.6 ou supérieur
- Nmap installé sur votre système
- Un environnement virtuel Python (recommandé)

## Installation

1. Installez Nmap sur votre système :
   - Sur macOS : `brew install nmap`
   - Sur Linux : `sudo apt-get install nmap`
   - Sur Windows : Téléchargez depuis [nmap.org](https://nmap.org/download.html)

2. Créez et activez un environnement virtuel (si ce n'est pas déjà fait) :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/macOS
# ou
.\venv\Scripts\activate  # Sur Windows
```

3. Installez les dépendances Python requises :
```bash
pip install -r requirements.txt
```

## Utilisation

Exécutez simplement le script :
```bash
python network_scanner.py
```

Le script va :
1. Détecter automatiquement votre interface réseau
2. Scanner tous les appareils connectés sur le réseau
3. Afficher pour chaque appareil :
   - Son adresse IP
   - Son adresse MAC
   - Son nom d'hôte (si disponible)

## Note

Ce script utilise Nmap pour scanner le réseau, ce qui est plus fiable et ne nécessite pas de droits administrateur dans la plupart des cas. 