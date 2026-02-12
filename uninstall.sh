#!/bin/bash
# =============================================================================
# PROJECT:      SteamMachine-DIY - Master Uninstaller
# VERSION:      1.0.0
# DESCRIPTION:  Completely remove SteamMachine-DIY components.
# =============================================================================

set -e

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Identity Detection ---
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo ./uninstall.sh)"
    exit 1
fi

REAL_USER=${SUDO_USER:-$(whoami)}
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo -e "${RED}!!! WARNING: This will remove all SteamMachine-DIY configurations !!!${NC}"
read -p "Are you sure you want to proceed? [y/N] " confirm
if [[ $confirm != [yY] ]]; then
    exit 1
fi

# --- 1. Remove System Files & Services ---
info "Removing system configurations..."
rm -f /etc/default/steamos-diy
rm -rf /etc/systemd/system/getty@tty1.service.d/
rm -f /usr/share/libalpm/hooks/gamescope-privs.hook

# --- 2. Remove Binaries & Helpers ---
info "Removing binaries and helpers..."
rm -f /usr/local/bin/steamos-*
rm -f /usr/local/bin/sdy
rm -rf /usr/local/bin/steamos-helpers/

# --- 3. Remove Desktop Entries ---
info "Removing desktop applications..."
rm -f /usr/local/share/applications/Control_Center.desktop
rm -f /usr/local/share/applications/Game_Mode.desktop
# Rimuove tutti i file .desktop che iniziano con steamos- se presenti
rm -f /usr/local/share/applications/steamos-*.desktop
update-desktop-database /usr/local/share/applications 2>/dev/null || true

# --- 4. Remove Shim Layer (Symlinks) ---
info "Removing symlinks in /usr/bin/..."
rm -f /usr/bin/steamos-session-select
rm -f /usr/bin/steamos-update
rm -rf /usr/bin/steamos-polkit-helpers/

# --- 5. Clean Bash Profile ---
info "Cleaning .bash_profile for user $REAL_USER..."
BP_FILE="$USER_HOME/.bash_profile"
if [ -f "$BP_FILE" ]; then
    # Rimuove il blocco di codice tra i tag STEAMOS-DIY TRIGGER
    sed -i '/# --- STEAMOS-DIY TRIGGER ---/,/# ---------------------------/d' "$BP_FILE"
fi

# --- 6. User Config (Optional) ---
read -p "Do you want to delete user configuration in ~/.config/steamOs? [y/N] " del_conf
if [[ $del_conf == [yY] ]]; then
    rm -rf "$USER_HOME/.config/steamOs"
    rm -rf "/etc/skel/.config/steamOs"
    success "User configurations removed."
fi

# --- 7. Reset Gamescope Capabilities ---
info "Resetting Gamescope capabilities..."
if [ -f /usr/bin/gamescope ]; then
    setcap -r /usr/bin/gamescope 2>/dev/null || true
fi

# --- 8. Finalization ---
info "Reloading system daemons..."
systemctl daemon-reload
# NOTA: Non disabilitiamo getty@tty1.service perché è essenziale per il login, 
# ma avendo rimosso l'override, tornerà al comportamento standard.

echo -e "\n${GREEN}==================================================${NC}"
success "UNINSTALLATION COMPLETE!"
echo -e "${GREEN}==================================================${NC}"
info "System restored to standard behavior."
warn "Note: Installed packages (steam, gamescope, etc.) were NOT removed."
echo -e "${GREEN}==================================================${NC}\n"
