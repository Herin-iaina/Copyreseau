Construction et utilisation du package d'installation Smartelia
=========================================================

Ce document explique comment construire et utiliser le package d'installation pour le client Smartelia.

Prérequis pour la construction
----------------------------
- Un Mac avec macOS 10.13 ou supérieur
- Les outils de développement Xcode (pour pkgbuild et productbuild)
- Les fichiers suivants dans le répertoire courant :
  * host_client.sh
  * com.smartelia.hostclient.plist
  * build_package.sh

Construction du package
---------------------
1. Ouvrir le Terminal
2. Se placer dans le répertoire contenant les fichiers
3. Rendre le script de construction exécutable :
   ```bash
   chmod +x build_package.sh
   ```
4. Exécuter le script de construction :
   ```bash
   ./build_package.sh
   ```

Le package sera créé dans le répertoire `output` sous le nom `SmarteliaClient-1.0.pkg`

Installation sur les clients
--------------------------
1. Double-cliquer sur le fichier `SmarteliaClient-1.0.pkg`
2. Suivre l'assistant d'installation
3. S'authentifier avec un compte administrateur si demandé

Le package va automatiquement :
- Installer les fichiers nécessaires
- Configurer les permissions
- Créer les fichiers de logs
- Démarrer le service

Vérification de l'installation
----------------------------
1. Vérifier que le service est actif :
   ```bash
   ps aux | grep host_client.sh
   ```

2. Vérifier les logs :
   ```bash
   cat /var/log/host_client.log
   ```

Désinstallation
-------------
Pour désinstaller le client :
1. Ouvrir le Finder
2. Aller dans le dossier Applications
3. Faire un clic droit sur "Smartelia Client"
4. Sélectionner "Déplacer vers la Corbeille"

Notes importantes
---------------
- Le package nécessite macOS 10.13 ou supérieur
- L'installation nécessite des droits administrateur
- Le client s'exécute automatiquement au démarrage
- Les logs sont conservés dans /var/log/host_client.log

Dépannage
--------
En cas de problème :
1. Vérifier les logs dans /var/log/host_client.log
2. Vérifier que le service est actif avec la commande ps
3. Redémarrer le service si nécessaire :
   ```bash
   sudo launchctl unload /Library/LaunchDaemons/com.smartelia.hostclient.plist
   sudo launchctl load /Library/LaunchDaemons/com.smartelia.hostclient.plist
   ``` 