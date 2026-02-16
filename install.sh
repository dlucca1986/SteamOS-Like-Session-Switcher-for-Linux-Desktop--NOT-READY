#!/bin/bash
# =============================================================================
# PROJECT:      SteamMachine-DIY - Master Installer 
# VERSION:      1.1.1 - Clean Path Correction
# DESCRIPTION:  Agnostic Installer for GitHub.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# =============================================================================

set -e 

# --- Colors & UI ---
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo ./install.sh)"
    exit 1
fi

REAL_USER=${SUDO_USER:-$(whoami)}
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
REAL_UID=$(id -u "$REAL_USER")

info "Starting installation for user: $REAL_USER"

# --- 1. File Deployment (Struttura Repo -> Sistema) ---
deploy_files() {
    info "Deploying project files..."

    # 1.1 Core Python Library
    mkdir -p /usr/local/lib/steamos_diy/helpers
    cp -r usr/local/lib/steamos_diy/* /usr/local/lib/steamos_diy/
    chmod 755 /usr/local/lib/steamos_diy/*.py
    chmod 755 /usr/local/lib/steamos_diy/helpers/*.py

    # 1.2 System Configurations (TTY1, Hooks, Desktop)
    mkdir -p /etc/systemd/system/getty@tty1.service.d/
    [ -f etc/systemd/system/getty@tty1.service.d/override.conf ] && \
        cp etc/systemd/system/getty@tty1.service.d/override.conf /etc/systemd/system/getty@tty1.service.d/ && \
        sed -i "s/\[USERNAME\]/$REAL_USER/g" /etc/systemd/system/getty@tty1.service.d/override.conf

    mkdir -p /usr/share/libalpm/hooks/
    [ -f usr/share/libalpm/hooks/gamescope-privs.hook ] && cp usr/share/libalpm/hooks/gamescope-privs.hook /usr/share/libalpm/hooks/

    mkdir -p /usr/local/share/applications/
    cp usr/local/share/applications/*.desktop /usr/local/share/applications/ 2>/dev/null || true

    # 1.3 Var Lib (Per il file next_session atomico)
    mkdir -p /var/lib/steamos_diy
    chown "$REAL_USER:$REAL_USER" /var/lib/steamos_diy

    # 1.4 Configurazione .config/steamos_diy (Skel & Home)
    mkdir -p /etc/skel/.config/steamos_diy
    cp -r etc/skel/.config/steamos_diy/* /etc/skel/.config/steamos_diy/ 2>/dev/null || true

    mkdir -p "$USER_HOME/.config/steamos_diy"
    cp -r etc/skel/.config/steamos_diy/* "$USER_HOME/.config/steamos_diy/" 2>/dev/null || true
    chown -R "$REAL_USER:$REAL_USER" "$USER_HOME/.config/steamos_diy"
}

# --- 2. Shim Layer (Symlinks) ---
setup_shim_links() {
    info "Creating SteamOS shim layer symlinks..."
    mkdir -p /usr/bin/steamos-polkit-helpers

    # Principali
    ln -sf /usr/local/lib/steamos_diy/session_launch.py /usr/bin/steamos-session-launch
    ln -sf /usr/local/lib/steamos_diy/session_select.py /usr/bin/steamos-session-select
    ln -sf /usr/local/lib/steamos_diy/sdy.py /usr/bin/sdy

    # Helpers & Polkit Compatibility
    ln -sf /usr/local/lib/steamos_diy/helpers/jupiter-biosupdate.py /usr/bin/jupiter-biosupdate
    ln -sf /usr/local/lib/steamos_diy/helpers/steamos-select-branch.py /usr/bin/steamos-select-branch
    ln -sf /usr/local/lib/steamos_diy/helpers/steamos-update.py /usr/bin/steamos-update
    
    ln -sf /usr/local/lib/steamos_diy/helpers/jupiter-biosupdate.py /usr/bin/steamos-polkit-helpers/jupiter-biosupdate
    ln -sf /usr/local/lib/steamos_diy/helpers/steamos-update.py /usr/bin/steamos-polkit-helpers/steamos-update
    ln -sf /usr/local/lib/steamos_diy/helpers/set-timezone.py /usr/bin/steamos-polkit-helpers/steamos-set-timezone
}

# --- 3. SSOTH Generation ---
generate_ssoth() {
    info "Generating /etc/default/steamos_diy.conf..."
    cat <<EOF > /etc/default/steamos_diy.conf
user=$REAL_USER
uid=$REAL_UID
next_session=/var/lib/steamos_diy/next_session
user_config=$USER_HOME/.config/steamos_diy/config
games_conf_dir=$USER_HOME/.config/steamos_diy/games.d
bin_gs=$(which gamescope)
bin_steam=$(which steam)
bin_plasma=$(which startplasma-wayland)
XDG_SESSION_TYPE=wayland
XDG_CURRENT_DESKTOP=KDE
KDE_WM_SYSTEMD_MANAGED=0
EOF
}

# --- 4. Finalizzazione ---
finalize() {
    systemctl daemon-reload
    systemctl enable getty@tty1.service
    success "INSTALLATION COMPLETE! Struttura coerente creata."
}

# --- Esecuzione ---
deploy_files
setup_shim_links
generate_ssoth
finalize
