#!/bin/bash

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher un titre
print_title() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Fonction pour obtenir l'utilisateur actuel
get_current_user() {
    whoami
}

# Fonction pour obtenir les informations sur la batterie
get_battery_info() {
    if [ -f "/usr/bin/pmset" ]; then
        BATTERY_INFO=$(pmset -g batt)
        BATTERY_PERCENT=$(echo "$BATTERY_INFO" | grep -o "[0-9]*%" | sed 's/%//')
        POWER_SOURCE=$(echo "$BATTERY_INFO" | grep -o "AC Power\|Battery Power")
        TIME_REMAINING=$(echo "$BATTERY_INFO" | grep -o "[0-9]*:[0-9]* remaining" | sed 's/ remaining//')
        
        echo "Niveau de batterie : $BATTERY_PERCENT%"
        echo "Alimentation secteur : $POWER_SOURCE"
        if [ ! -z "$TIME_REMAINING" ]; then
            echo "Temps restant : $TIME_REMAINING"
        fi
    else
        echo "Impossible d'obtenir les informations sur la batterie"
    fi
}

# Fonction pour obtenir les ressources système
get_system_resources() {
    # CPU
    CPU_CORES=$(sysctl -n hw.ncpu)
    CPU_USAGE=$(ps -A -o %cpu | awk '{s+=$1} END {print s}')
    CPU_USAGE=$(echo "scale=1; $CPU_USAGE / $CPU_CORES" | bc)
    
    # Mémoire
    MEMORY_TOTAL=$(sysctl -n hw.memsize | awk '{print $0/1024/1024/1024}')
    MEMORY_USED=$(vm_stat | awk '/active/ {print $3}' | sed 's/\.//')
    MEMORY_USED=$(echo "scale=2; $MEMORY_USED * 4096 / 1024 / 1024 / 1024" | bc)
    MEMORY_PERCENT=$(echo "scale=1; ($MEMORY_USED / $MEMORY_TOTAL) * 100" | bc)
    
    # Disque
    DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}' | sed 's/G//')
    DISK_USED=$(df -h / | awk 'NR==2 {print $3}' | sed 's/G//')
    DISK_FREE=$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')
    DISK_PERCENT=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    echo "CPU : $CPU_USAGE% ($CPU_CORES cœurs)"
    echo "Mémoire : $MEMORY_PERCENT% utilisée ($MEMORY_USED GB sur $MEMORY_TOTAL GB)"
    echo "Disque : $DISK_PERCENT% utilisé ($DISK_FREE GB libre sur $DISK_TOTAL GB)"
}

# Fonction pour obtenir les applications en cours d'exécution
get_running_apps() {
    echo "Applications en cours d'exécution :"
    
    # Utiliser osascript pour obtenir la liste des applications actives
    osascript <<EOF
    tell application "System Events"
        set appList to name of every process where background only is false
    end tell
    set output to ""
    repeat with appName in appList
        set output to output & appName & "\n"
    end repeat
    return output
EOF
}

# Fonction pour obtenir les détails d'une application
get_app_details() {
    local app_name=$1
    local total_cpu=0
    local total_mem=0
    local pids=()
    
    # Obtenir tous les PIDs pour cette application
    while read -r pid; do
        if [ ! -z "$pid" ]; then
            pids+=("$pid")
            # Obtenir CPU et mémoire pour ce PID
            cpu=$(ps -p "$pid" -o %cpu= 2>/dev/null)
            mem=$(ps -p "$pid" -o %mem= 2>/dev/null)
            if [ ! -z "$cpu" ]; then
                total_cpu=$(echo "$total_cpu + $cpu" | bc)
            fi
            if [ ! -z "$mem" ]; then
                total_mem=$(echo "$total_mem + $mem" | bc)
            fi
        fi
    done < <(pgrep -f "$app_name")
    
    # Afficher les détails
    if [ ${#pids[@]} -gt 0 ]; then
        echo -e "\nApplication : $app_name"
        echo "  PIDs : ${pids[*]}"
        echo "  CPU total : $(printf "%.1f" $total_cpu)%"
        echo "  Mémoire totale : $(printf "%.1f" $total_mem)%"
    fi
}

# Fonction principale
main() {
    print_title "Informations Système"
    
    # Utilisateur actuel
    echo "Utilisateur actuel : $(get_current_user)"
    
    # Batterie
    print_title "Informations Batterie"
    get_battery_info
    
    # Ressources système
    print_title "Ressources Système"
    get_system_resources
    
    # Applications en cours
    print_title "Applications en cours d'exécution"
    while read -r app_name; do
        if [ ! -z "$app_name" ]; then
            get_app_details "$app_name"
        fi
    done < <(get_running_apps)
}

# Exécution du script
main 