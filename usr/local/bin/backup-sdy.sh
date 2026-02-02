#!/bin/bash
# =============================================================================
# SteamOS-DIY - Full System Snapshot & Recovery Tool
# =============================================================================
set -e

BACKUP_NAME="SteamOS-DIY_Full_Backup_$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/home/lelo/SteamOS-DIY_Backup/$BACKUP_NAME"
LOG_FILE="/var/log/steamos-diy-backup.log"

# Lista dei componenti critici (Percorsi reali puliti)
TARGETS=(
    "/etc/default/steamos-diy"
    "/usr/local/bin/steamos-session-launch"
    "/usr/local/bin/steamos-session-select"
    "/etc/systemd/system/steamos-gamemode@.service"
    "/etc/systemd/system/steamos-desktop@.service"
    "/etc/systemd/system/steamos-exit-splash.service"  # Corretto qui
    "/etc/systemd/system/getty@tty1.service.d/autologin.conf"
    "/etc/systemd/system/graphical.target.wants/"
    "/usr/local/bin/steamos-helpers/"
    "/usr/local/bin/sdy"
    "/usr/local/bin/backup-sdy.sh"
    "/etc/default/grub"                                # Corretto qui
    "/etc/grub.d/10_linux"                            # Corretto qui
)

# Funzione per loggare con coerenza SDY
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Backup-SDY] $1" | tee -a "$LOG_FILE"
}

if [[ $EUID -ne 0 ]]; then
   echo "Questo script deve essere eseguito come ROOT (sudo)."
   exit 1
fi

log "Inizio snapshot totale del sistema..."
mkdir -p "$BACKUP_DIR"

# --- 1. CLONAZIONE STRUTTURA E PERMESSI ---
for item in "${TARGETS[@]}"; do
    if [[ -e "$item" ]]; then
        # Creiamo la struttura cartelle identica dentro il backup
        DEST_PATH="$BACKUP_DIR$(dirname "$item")"
        mkdir -p "$DEST_PATH"
        cp -a "$item" "$DEST_PATH/"
        log "Snapshot: $item -> OK"
    else
        log "WARN: $item non trovato, saltato."
    fi
done

# --- 2. DUMP DEI LINK SIMBOLICI ---
log "Archiviazione mappatura link simbolici..."
ls -la /usr/bin/steamos-* /usr/bin/sdy > "$BACKUP_DIR/symbolic_links_map.txt" 2>/dev/null || true

# --- 3. CREAZIONE ARCHIVIO ---
cd /home/lelo/SteamOS-DIY_Backup/
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
chown lelo:lelo "${BACKUP_NAME}.tar.gz"

log "Backup completato: ${BACKUP_NAME}.tar.gz"
