#!/bin/bash
# =============================================================================
# SteamMachine-DIY - Master Installer (v3.1.5)
# Fixed: Autologin placeholder, desktop entry discovery & menu update
# =============================================================================

set -uo pipefail

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
APP_ENTRIES="/usr/local/share/applications"
HOOK_DIR="/etc/pacman.d/hooks"
LOG_FILE="/var/log/steamos-diy.log"

info()    { echo -e "${CYAN}[SYSTEM]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Intestazione ---
clear
echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}   SteamOS-DIY Master Installer v3.1.5        ${NC}"
echo -e "${CYAN}==============================================${NC}"

if [[ $EUID -ne 0 ]]; then
    error "This script must be run with sudo."
fi

install_dependencies() {
    info "Verifying hardware and installing dependencies..."
    if ! grep -q "^\[multilib\]" /etc/pacman.conf; then
        echo -e "\n[multilib]\nInclude = /etc/pacman.d/mirrorlist" >> /etc/pacman.conf
        pacman -Sy
    fi

    local pkgs=(steam gamescope xorg-xwayland mangohud lib32-mangohud gamemode lib32-gamemode vulkan-icd-loader lib32-vulkan-icd-loader mesa-utils python-pyqt6 pciutils procps-ng)
    if lspci | grep -iq "AMD"; then
        pkgs+=(vulkan-radeon lib32-vulkan-radeon)
    elif lspci | grep -iq "Intel"; then
        pkgs+=(vulkan-intel lib32-vulkan-intel)
    fi

    pacman -S --needed --noconfirm "${pkgs[@]}"
}

deploy_core() {
    info "Deploying Agnostic Core..."
    mkdir -p "$HELPERS_DEST" "$SYSTEMD_DEST/getty@tty1.service.d" "$APP_ENTRIES" "$POLKIT_LINKS_DIR"

    # 1. Scripts
    cp -r "$SOURCE_DIR/usr/local/bin/"* "$BIN_DEST/" 2>/dev/null || warn "Binaries not found in source."
    chmod +x "$BIN_DEST/steamos-session-launch" "$BIN_DEST/steamos-diy-control" "$BIN_DEST/sdy" 2>/dev/null || true

    if [ -d "$HELPERS_DEST" ]; then
        chmod +x "$HELPERS_DEST/"* 2>/dev/null || true
    fi

    # 2. Systemd & Autologin (FIXED PLACEHOLDER)
    cp "$SOURCE_DIR/etc/systemd/system/steamos-"*@.service "$SYSTEMD_DEST/" 2>/dev/null || true
    cp "$SOURCE_DIR/etc/systemd/system/steamos-exit-splash.service" "$SYSTEMD_DEST/" 2>/dev/null || true

    local AUTO_PATH="$SYSTEMD_DEST/getty@tty1.service.d/autologin.conf"
    if [ -f "$SOURCE_DIR/etc/systemd/system/getty@tty1.service.d/autologin.conf" ]; then
        cp "$SOURCE_DIR/etc/systemd/system/getty@tty1.service.d/autologin.conf" "$AUTO_PATH"
        sed -i "s/\[USERNAME\]/$REAL_USER/g" "$AUTO_PATH"
        info "Autologin calibrated for user: $REAL_USER"
    fi

    # 3. Desktop entries (IMPROVED DISCOVERY)
    # Cerca i .desktop in entrambi i percorsi possibili del repo
    for dir in "usr/local/share/applications" "usr/share/applications"; do
        if [[ -d "$SOURCE_DIR/$dir" ]]; then
            cp "$SOURCE_DIR/$dir/steamos-"*.desktop "$APP_ENTRIES/" 2>/dev/null || true
        fi
    done

    # Aggiorna il database delle applicazioni per i menu
    update-desktop-database "$APP_ENTRIES" 2>/dev/null || true
}

setup_system() {
    info "Configuring system environment..."
    for grp in sys tty rfkill video storage render lp input audio wheel autologin; do
        groupadd -f "$grp"
        usermod -aG "$grp" "$REAL_USER"
    done

    if [[ -f "$SOURCE_DIR/etc/default/steamos-diy" ]]; then
        cp "$SOURCE_DIR/etc/default/steamos-diy" "$GLOBAL_CONF"
        sed -i "s/STEAMOS_USER=.*/STEAMOS_USER=\"$REAL_USER\"/" "$GLOBAL_CONF"
    else
        echo "STEAMOS_USER=\"$REAL_USER\"" > "$GLOBAL_CONF"
    fi
    touch "$LOG_FILE" && chmod 666 "$LOG_FILE"

    for dm in sddm gdm lightdm; do
        if systemctl is-enabled --quiet "$dm" 2>/dev/null; then
            info "Disabling $dm to prevent TTY conflicts..."
            systemctl disable "$dm" 2>/dev/null || true
        fi
    done
}

setup_security() {
    info "Configuring Sudoers & Hooks..."
    mkdir -p /etc/sudoers.d
    if [ -f "$SOURCE_DIR/etc/sudoers.d/steamos-diy" ]; then
        cp "$SOURCE_DIR/etc/sudoers.d/steamos-diy" "$SUDOERS_FILE"
        chmod 440 "$SUDOERS_FILE"
    fi

    ln -sf "$BIN_DEST/steamos-session-launch" "/usr/bin/steamos-session-launch"
    ln -sf "$BIN_DEST/steamos-session-select" "/usr/bin/steamos-session-select"

    if ls "$HELPERS_DEST/"* >/dev/null 2>&1; then
        for helper in "$HELPERS_DEST"/*; do
            ln -sf "$helper" "$POLKIT_LINKS_DIR/$(basename "$helper")"
        done
    fi

    mkdir -p "$HOOK_DIR"
    cat <<EOF > "$HOOK_DIR/gamescope-capabilities.hook"
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = gamescope
[Action]
Description = Restoring Gamescope capabilities...
When = PostTransaction
Exec = /usr/bin/setcap 'cap_sys_admin,cap_sys_nice,cap_ipc_lock+ep' /usr/bin/gamescope
EOF
}

enable_services() {
    info "Activating systemd units..."
    systemctl daemon-reload
    systemctl enable "steamos-gamemode@${REAL_USER}.service" 2>/dev/null || true

    if [[ -x /usr/bin/gamescope ]]; then
        setcap 'cap_sys_admin,cap_sys_nice,cap_ipc_lock+ep' /usr/bin/gamescope 2>/dev/null || true
    fi
}

# --- Execution ---
install_dependencies
deploy_core
setup_system
setup_security
enable_services

echo -e "\n${GREEN}==============================================${NC}"
success "Installation Successful! Now let's double check."
echo -e "${GREEN}==============================================${NC}"
