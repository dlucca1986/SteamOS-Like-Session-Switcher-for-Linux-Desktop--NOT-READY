#!/bin/bash
# =============================================================================
# SteamMachine-DIY - Master Installer (v3.1.0+)
# Architecture: Systemd-Agnostic / Zero-DM
# =============================================================================

set -eou pipefail

# --- Environment & Colors ---
export LANG=C
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SOURCE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REAL_USER=${SUDO_USER:-$(whoami)}
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

# --- Destination Paths ---
BIN_DEST="/usr/local/bin"
HELPERS_DEST="/usr/local/bin/steamos-helpers"
POLKIT_LINKS_DIR="/usr/bin/steamos-polkit-helpers"
SYSTEMD_DEST="/etc/systemd/system"
SUDOERS_FILE="/etc/sudoers.d/steamos-diy"
GLOBAL_CONF="/etc/default/steamos-diy"
PIXMAPS_DEST="/usr/local/share/pixmaps"
APP_ENTRIES="/usr/local/share/applications"
LOG_FILE="/var/log/steamos-diy.log"

# --- UI Functions ---
info()    { echo -e "${CYAN}[SYSTEM]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

check_privileges() {
    [[ $EUID -ne 0 ]] && error "Run with sudo (e.g., sudo ./install.sh)"
}

install_dependencies() {
    info "Verifying hardware and installing dependencies..."
    
    # Ensure Multilib
    if ! grep -q "^\[multilib\]" /etc/pacman.conf; then
        sed -i '/^#\[multilib\]/,+1 s/^#//' /etc/pacman.conf
        pacman -Sy
    fi

    # Base Packages + NEW python-pyqt6
    local pkgs=(
        steam gamescope xorg-xwayland mangohud lib32-mangohud 
        gamemode lib32-gamemode vulkan-icd-loader lib32-vulkan-icd-loader 
        mesa-utils python-pyqt6 pciutils procps-ng
    )

    # Hardware detection (from legacy)
    if lspci | grep -iq "AMD"; then pkgs+=(vulkan-radeon lib32-vulkan-radeon);
    elif lspci | grep -iq "Intel"; then pkgs+=(vulkan-intel lib32-vulkan-intel); fi

    pacman -S --needed --noconfirm "${pkgs[@]}" || error "Failed to install packages."
}

deploy_core() {
    info "Deploying Agnostic Core..."
    
    # 1. Scripts
    mkdir -p "$HELPERS_DEST"
    cp -r "$SOURCE_DIR/usr/local/bin/"* "$BIN_DEST/"
    chmod +x "$BIN_DEST/steamos-session-launch"
    chmod +x "$BIN_DEST/steamos-diy-control"
    chmod +x "$HELPERS_DEST/"*

    # 2. Systemd Services
    cp "$SOURCE_DIR/etc/systemd/system/steamos-"*@.service "$SYSTEMD_DEST/"
    
    # 3. Assets (Icons & Desktop)
    mkdir -p "$PIXMAPS_DEST" "$APP_ENTRIES"
    cp "$SOURCE_DIR/usr/local/share/pixmaps/"* "$PIXMAPS_DEST/"
    cp "$SOURCE_DIR/usr/local/share/applications/"* "$APP_ENTRIES/"
}

setup_global_config() {
    info "Generating Global System Configuration..."
    
    cat <<EOF > "$GLOBAL_CONF"
# SteamOS-DIY Global Configuration
STEAMOS_USER="$REAL_USER"
LOG_TAG="[SteamOS-DIY]"
LOG_FILE="$LOG_FILE"
CONF_DIR="$USER_HOME/.config/steamos-diy"
EOF
    
    # Initialize Log
    touch "$LOG_FILE" && chmod 666 "$LOG_FILE"
}

setup_security() {
    info "Configuring Sudoers & Services..."
    
    # Sudoers Policy
    cp "$SOURCE_DIR/etc/sudoers.d/steamos-diy" "$SUDOERS_FILE"
    chmod 440 "$SUDOERS_FILE"

    # Symlinks (Compatibility)
    mkdir -p "$POLKIT_LINKS_DIR"
    ln -sf "$BIN_DEST/steamos-session-launch" "/usr/bin/steamos-session-launch"
    ln -sf "$BIN_DEST/steamos-session-select" "/usr/bin/steamos-session-select"
    
    # Helper links for Steam Polkit
    for helper in "$HELPERS_DEST"/*; do
        ln -sf "$helper" "$POLKIT_LINKS_DIR/$(basename "$helper")"
    done

    # Enable Service for current user
    systemctl daemon-reload
    systemctl enable "steamos-gamemode@${REAL_USER}.service"
}

# --- Main Execution ---
check_privileges
install_dependencies
deploy_core
setup_global_config
setup_security

# Gamescope Capabilities Hook
if [[ -x /usr/bin/gamescope ]]; then
    setcap 'cap_sys_admin,cap_sys_nice,cap_ipc_lock+ep' /usr/bin/gamescope 2>/dev/null || true
fi

success "Installation Successful! Reboot to enter Gaming Mode."
