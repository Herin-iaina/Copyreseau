#!/bin/bash

# Configuration
SERVER_URL="http://172.17.19.26:5001"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/host_client.log"
PID_FILE="$PROJECT_DIR/host_client.pid"
# CHECK_INTERVAL=10  # 10 secondes pour le debug
CHECK_INTERVAL=3600  # 1h pour la production
MAX_RETRIES=3  # Nombre maximum de tentatives de connexion
RETRY_DELAY=60  # Délai entre les tentatives en secondes

# Création des répertoires nécessaires
mkdir -p "$LOG_DIR"

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
    ipconfig getifaddr en0 || ipconfig getifaddr en1
}

# Fonction pour obtenir les informations sur la batterie
get_battery_info() {
    if [ -f "/usr/bin/pmset" ]; then
        local battery_info=$(pmset -g batt)
        local percent=$(echo "$battery_info" | grep -o "[0-9]*%" | sed 's/%//')
        local power_source=$(echo "$battery_info" | grep -o "AC Power\|Battery Power")
        local time_remaining=$(echo "$battery_info" | grep -o "[0-9]*:[0-9]* remaining" | sed 's/ remaining//')
        
        echo "{\"percent\":$percent,\"power_plugged\":$(if [ "$power_source" = "AC Power" ]; then echo "true"; else echo "false"; fi),\"time_left\":\"$time_remaining\"}"
    else
        echo "null"
    fi
}

# Fonction pour obtenir les informations CPU
get_cpu_info() {
    local cpu_cores=$(sysctl -n hw.ncpu)
    # Additionne tous les %cpu, puis divise par le nombre de cœurs pour obtenir un pourcentage global max 100%
    local total_cpu=$(ps -A -o %cpu | awk '{s+=$1} END {print s}')
    local cpu_usage=$(echo "scale=1; $total_cpu / $cpu_cores" | bc)
    echo "{\"percent\":$cpu_usage,\"count\":$cpu_cores}"
}

# Fonction pour obtenir les informations mémoire
get_memory_info() {
    local pagesize=$(vm_stat | grep "page size of" | awk '{print $8}')
    local mem_used_pages=$(vm_stat | awk '/Pages active/ {a=$3} /Pages wired down/ {w=$4} /Pages occupied by compressor/ {c=$5} END {gsub(/\./, "", a); gsub(/\./, "", w); gsub(/\./, "", c); print a+w+c}')
    local mem_used_bytes=$((mem_used_pages * pagesize))
    local mem_used_gb=$(echo "scale=2; $mem_used_bytes/1024/1024/1024" | bc)
    local mem_total_bytes=$(sysctl -n hw.memsize)
    local mem_total_gb=$(echo "scale=2; $mem_total_bytes/1024/1024/1024" | bc)
    local mem_free_bytes=$(($mem_total_bytes - $mem_used_bytes))
    local mem_free_gb=$(echo "scale=2; $mem_free_bytes/1024/1024/1024" | bc)
    local percent=$(echo "scale=1; ($mem_used_gb / $mem_total_gb) * 100" | bc)
    echo "{\"total\":$mem_total_gb,\"used\":$mem_used_gb,\"available\":$mem_free_gb,\"percent\":$percent}"
}

# Fonction pour obtenir les informations disque
get_disk_info() {
    # Utilise df -H pour avoir les valeurs en Go
    local total=$(df -H / | awk 'NR==2 {print $2}' | sed 's/G//')
    local used=$(df -H / | awk 'NR==2 {print $3}' | sed 's/G//')
    local free=$(df -H / | awk 'NR==2 {print $4}' | sed 's/G//')
    local percent=$(df -H / | awk 'NR==2 {print $5}' | sed 's/%//')
    echo "{\"total\":$total,\"used\":$used,\"free\":$free,\"percent\":$percent}"
}

# Fonction pour obtenir les applications en cours d'exécution
get_running_apps() {
    local apps_json="{"
    local first=true
    
    # Lire les applications une par une
    while IFS= read -r app_name; do
        if [ ! -z "$app_name" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                apps_json+=","
            fi
            # Nettoyer le nom de l'application
            app_name=$(echo "$app_name" | tr -d '\r' | tr -d '\n' | tr -d ',')
            apps_json+="\"$app_name\":true"
        fi
    done < <(osascript -e 'tell application "System Events" to get name of every process where background only is false' | tr ',' '\n')
    
    apps_json+="}"
    echo "$apps_json"
}

# Fonction pour obtenir les informations système
get_system_info() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local hostname=$(get_hostname)
    local ip=$(get_ip)
    local current_user=$(whoami)
    
    # Obtenir les statistiques réseau
    local bytes_sent=$(netstat -ib | awk '/en0/ {print $7}' | head -n1)
    local bytes_recv=$(netstat -ib | awk '/en0/ {print $10}' | head -n1)
    
    # Construire le JSON en mémoire
    local json_data="{
    \"timestamp\": \"$timestamp\",
    \"hostname\": \"$hostname\",
    \"ip\": \"$ip\",
    \"system_info\": {
        \"cpu\": $(get_cpu_info),
        \"memory\": $(get_memory_info),
        \"disk\": $(get_disk_info),
        \"battery\": $(get_battery_info),
        \"current_user\": \"$current_user\",
        \"running_apps\": $(get_running_apps),
        \"boot_time\": \"$(date -r $(sysctl -n kern.boottime | awk '{print $4}' | sed 's/,//') "+%Y-%m-%d %H:%M:%S")\",
        \"network\": {
            \"bytes_sent\": $bytes_sent,
            \"bytes_recv\": $bytes_recv
        }
    }
}"
    echo "$json_data"
}

# Fonction pour envoyer les informations au serveur
send_info_to_server() {
    # Vérifier si le serveur est accessible
    if ! check_server; then
        log "ERROR" "Serveur inaccessible après $MAX_RETRIES tentatives"
        return 1
    fi
    
    # Obtenir les informations système
    local system_info=$(get_system_info)
    log "DEBUG" "Envoi des informations système: $system_info"
    
    # Envoyer les données système au serveur
    local system_response=$(curl -s -X POST -H "Content-Type: application/json" -d "$system_info" "$SERVER_URL/system_info")
    local system_status=$?
    
    if [ $system_status -eq 0 ] && [[ ! "$system_response" =~ "error" ]]; then
        # Envoyer les informations de base pour la compatibilité
        local basic_info="{\"hostname\":\"$(get_hostname)\",\"ip\":\"$(get_ip)\"}"
        local basic_response=$(curl -s -X POST -H "Content-Type: application/json" -d "$basic_info" "$SERVER_URL/report")
        local basic_status=$?
        
        if [ $basic_status -eq 0 ] && [[ ! "$basic_response" =~ "error" ]]; then
            log "INFO" "Informations envoyées avec succès"
            return 0
        else
            log "ERROR" "Erreur lors de l'envoi des informations de base: $basic_response"
            return 1
        fi
    else
        log "ERROR" "Erreur lors de l'envoi des informations système: $system_response"
        return 1
    fi
}

# Fonction pour écrire le PID
write_pid_file() {
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