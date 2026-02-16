#!/bin/bash
# =============================================================================
# PROJECT:      SteamMachine-DIY - Master Uninstaller
# VERSION:      1.0.0
# DESCRIPTION:  Complete removal of DIY components and trigger cleanup.
# PHILOSOPHY:   Leave no trace (but keep system dependencies).
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

if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo ./uninstall.sh)"
    exit 1
fi

REAL_USER=${SUDO_USER:-$(whoami)}
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo -e "${RED}"
echo "=================================================="
echo "      SteamMachine-DIY UNINSTALLER                "
echo "=================================================="
echo -e "${NC}"

# --- 1. Remove Triggers ---
cleanup_triggers() {
    info "Removing trigger from .bash_profile..."
    BP_FILE="$USER_HOME/.bash_profile"
    if [ -f "$BP_FILE" ]; then
        # Rimuove tutto ciò che sta tra i tag BEGIN ed END (inclusi i tag)
        sed -i '/# --- BEGIN STEAMOS-DIY TRIGGER ---/,/# --- END STEAMOS-DIY TRIGGER ---/d' "$BP_FILE"
        success "Bash profile cleaned."
    fi

    info "Removing TTY1 autologin override..."
    rm -rf /etc/systemd/system/getty@tty1.service.d/
    success "TTY1 override removed."
}

# --- 2. Remove Shim Layer & Binaries ---
cleanup_files() {
    info "Deleting symlinks and shim layer..."
    SYMLINKS=(
        "/usr/bin/steamos-session-launch"
        "/usr/bin/steamos-session-select"
        "/usr/bin/sdy"
        "/usr/bin/sdy-backup"
        "/usr/bin/sdy-restore"
        "/usr/bin/jupiter-biosupdate"
        "/usr/bin/steamos-select-branch"
        "/usr/bin/steamos-update"
        "/usr/bin/steamos-polkit-helpers"
    )

    for link in "${SYMLINKS[@]}"; do
        [ -L "$link" ] || [ -d "$link" ] && rm -rf "$link" && echo "  - Removed $link"
    done

    info "Deleting core library..."
    rm -rf /usr/local/lib/steamos_diy
    
    info "Deleting system configurations..."
    rm -f /etc/default/steamos_diy.conf
    rm -f /usr/share/libalpm/hooks/gamescope-privs.hook
    
    info "Deleting state directory..."
    rm -rf /var/lib/steamos_diy
    
    success "Filesystem cleaned."
}

# --- 3. Restore Display Manager ---
restore_dm() {
    warn "SteamMachine-DIY is disabled. You might need a Display Manager to boot into a GUI."
    echo -ne "${YELLOW}Would you like to enable a Display Manager? (e.g., sddm, gdm, lightdm) [n]: ${NC}"
    read -r dm_name
    if [[ -n "$dm_name" ]]; then
        if systemctl list-unit-files | grep -q "^$dm_name.service"; then
            systemctl enable "$dm_name"
            success "$dm_name enabled."
        else
            error "Service $dm_name not found."
        fi
    fi
}

# --- 4. Finalization ---
finalize() {
    systemctl daemon-reload
    echo -e "\n${GREEN}==================================================${NC}"
    success "UNINSTALLATION COMPLETE!"
    info "Note: Core dependencies (Steam, Gamescope, etc.) were NOT removed."
    warn "Please REBOOT to apply changes."
    echo -e "${GREEN}==================================================${NC}\n"
}

# --- Execution ---
echo -ne "${RED}Are you sure you want to completely remove SteamMachine-DIY? [y/N] ${NC}"
read -r confirm
if [[ $confirm == [yY] ]]; then
    cleanup_triggers
    cleanup_files
    restore_dm
    finalize
else
    info "Uninstall aborted."
fi
