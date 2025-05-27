#!/bin/bash

# Configuration
SERVER_URL="http://localhost:5001"
LOG_FILE="/var/log/host_client.log"
PID_FILE="/var/run/host_client.pid"
CHECK_INTERVAL=3600  # 1 heure en secondes
MAX_RETRIES=3  # Nombre maximum de tentatives de connexion
RETRY_DELAY=60  # Délai entre les tentatives en secondes

# Fonction de logging
log() {
    local level=$1
    local message=$2
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    echo "[$timestamp] [$level] $message"
}

# Fonction pour vérifier si le serveur est accessible
check_server() {
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s "$SERVER_URL/status" > /dev/null; then
            return 0
        fi
        retries=$((retries + 1))
        if [ $retries -lt $MAX_RETRIES ]; then
            log "WARNING" "Serveur inaccessible, nouvelle tentative dans $RETRY_DELAY secondes..."
            sleep $RETRY_DELAY
        fi
    done
    return 1
}

# Fonction pour obtenir le nom d'hôte
get_hostname() {
    hostname
}

# Fonction pour obtenir l'adresse IP
get_ip() {
    # Attendre que l'interface réseau soit prête
    local max_wait=30
    local wait_time=0
    local ip=""
    
    while [ $wait_time -lt $max_wait ]; do
        ip=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
        if [ ! -z "$ip" ]; then
            echo "$ip"
            return 0
        fi
        sleep 1
        wait_time=$((wait_time + 1))
    done
    
    # Si aucune IP n'est trouvée, essayer une dernière fois
    ipconfig getifaddr en0 || ipconfig getifaddr en1
}

# Fonction pour envoyer les informations au serveur
send_info_to_server() {
    local hostname=$(get_hostname)
    local ip=$(get_ip)
    
    if [ -z "$hostname" ] || [ -z "$ip" ]; then
        log "ERROR" "Impossible de récupérer le nom d'hôte ou l'adresse IP"
        return 1
    fi
    
    # Vérifier si le serveur est accessible
    if ! check_server; then
        log "ERROR" "Serveur inaccessible après $MAX_RETRIES tentatives"
        return 1
    fi
    
    # Préparer les données JSON
    local json_data="{\"hostname\":\"$hostname\",\"ip\":\"$ip\"}"
    
    # Envoyer les données au serveur
    local response=$(curl -s -X POST -H "Content-Type: application/json" -d "$json_data" "$SERVER_URL/report")
    
    if [ $? -eq 0 ]; then
        log "INFO" "Informations envoyées avec succès: $hostname ($ip)"
        return 0
    else
        log "ERROR" "Erreur lors de l'envoi des informations: $response"
        return 1
    fi
}

# Fonction pour écrire le PID
write_pid_file() {
    # Créer le répertoire si nécessaire
    mkdir -p "$(dirname "$PID_FILE")"
    echo $$ > "$PID_FILE"
}

# Fonction pour supprimer le fichier PID
remove_pid_file() {
    [ -f "$PID_FILE" ] && rm "$PID_FILE"
}

# Gestionnaire de signaux
cleanup() {
    log "INFO" "Arrêt du daemon..."
    remove_pid_file
    exit 0
}

# Configuration des signaux
trap cleanup SIGTERM SIGINT

# Fonction principale du daemon
run_daemon() {
    # Créer le répertoire de log si nécessaire
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    
    # Écrire le PID
    write_pid_file
    
    log "INFO" "Démarrage du daemon"
    
    # Attendre que le réseau soit prêt
    log "INFO" "Attente de la connexion réseau..."
    sleep 30
    
    # Boucle principale
    while true; do
        send_info_to_server
        sleep "$CHECK_INTERVAL"
    done
}

# Vérifier si le daemon est déjà en cours d'exécution
if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        log "ERROR" "Le daemon est déjà en cours d'exécution (PID: $pid)"
        exit 1
    else
        remove_pid_file
    fi
fi

# Démarrer le daemon
run_daemon 