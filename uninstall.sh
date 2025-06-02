#!/bin/bash

# Fonction pour afficher les messages
log() {
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1"
}

# Vérifier si le script est exécuté en tant que root
if [ "$EUID" -ne 0 ]; then
    log "❌ Ce script doit être exécuté en tant que root (sudo)"
    exit 1
fi

# Arrêter et décharger le LaunchDaemon
log "🛑 Arrêt du service..."
if [ -f "/Library/LaunchDaemons/com.smartelia.hostclient.plist" ]; then
    launchctl unload "/Library/LaunchDaemons/com.smartelia.hostclient.plist" 2>/dev/null
    sleep 2
fi

# Supprimer les fichiers installés
log "🗑️ Suppression des fichiers..."
rm -f "/Library/LaunchDaemons/com.smartelia.hostclient.plist"
rm -f "/usr/local/bin/host_client.sh"
rm -f /var/log/host_client.* 2>/dev/null

# Supprimer le script de désinstallation lui-même
log "🧹 Nettoyage final..."
rm -f "$0"

log "✅ Désinstallation terminée avec succès !" 