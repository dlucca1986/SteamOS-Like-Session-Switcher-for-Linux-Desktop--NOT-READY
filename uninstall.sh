#!/bin/bash
# =============================================================================
# SteamMachine-DIY - Master Uninstaller
# Architecture: Systemd-Agnostic / Zero-DM Cleanup
# Description: Fully removes SteamOS-DIY components and restores system state.
# Repository: https://github.com/dlucca1986/SteamMachine-DIY
# =============================================================================

set -eou pipefail

# --- Environment & Colors ---
export LANG=C
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# User detection from global config
GLOBAL_CONF="/etc/default/steamos-diy"
if [[ -f "$GLOBAL_CONF" ]]; then
    # Source global config to identify the managed user
    source "$GLOBAL_CONF"
    REAL_USER="$STEAMOS_USER"
else
    # Fallback to current sudo user or logged user
    REAL_USER=${SUDO_USER:-$(whoami)}
fi
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

# --- Paths ---
BIN_DEST="/usr/local/bin"
HELPERS_DEST="/usr/local/bin/steamos-helpers"
POLKIT_LINKS_DIR="/usr/bin/steamos-polkit-helpers"
SYSTEMD_DEST="/etc/systemd/system"
SUDOERS_FILE="/etc/sudoers.d/steamos-diy"
APP_ENTRIES="/usr/local/share/applications"
HOOK_FILE="/etc/pacman.d/hooks/gamescope-capabilities.hook"
LOG_FILE="/var/log/steamos-diy.log"
CONFIG_DIR="$USER_HOME/.config/steamos-diy"

# --- UI Functions ---
info()    { echo -e "${CYAN}[UNINSTALL]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Root privilege check
[[ $EUID -ne 0 ]] && echo "Please run as root (sudo)." && exit 1

# --- 1. Disable Services ---
info "Stopping and disabling systemd units..."
# Safely stop and disable all specific SteamOS-DIY services
systemctl stop "steamos-gamemode@${REAL_USER}.service" 2>/dev/null || true
systemctl disable "steamos-gamemode@${REAL_USER}.service" 2>/dev/null || true
systemctl disable "steamos-desktop@${REAL_USER}.service" 2>/dev/null || true
systemctl disable "steamos-exit-splash.service" 2>/dev/null || true

# --- 2. File Cleanup ---
info "Removing binaries, services, and configurations..."
# Remove specialized helper directories
rm -rf "$HELPERS_DEST"

# Remove core binaries and the master control CLI
rm -f "$BIN_DEST/steamos-session-launch" "$BIN_DEST/steamos-session-select" \
      "$BIN_DEST/steamos-diy-control" "$BIN_DEST/sdy"

# Remove systemd unit files and drop-in configurations
rm -f "$SYSTEMD_DEST/steamos-"*@.service
rm -f "$SYSTEMD_DEST/steamos-exit-splash.service"
rm -rf "$SYSTEMD_DEST/getty@tty1.service.d"

# Remove system-level config, hooks, and logs
rm -f "$SUDOERS_FILE" "$HOOK_FILE" "$GLOBAL_CONF" "$LOG_FILE"

# Remove application menu entries (KDE/GNOME)
rm -f "$APP_ENTRIES/steamos-diy-control.desktop" \
      "$APP_ENTRIES/steamos-switch-gamemode.desktop"

# --- 3. Symlinks Cleanup ---
info "Removing compatibility symlinks..."
# Clean up global symlinks created during installation
rm -f "/usr/bin/steamos-session-launch" "/usr/bin/steamos-session-select" \
      "/usr/bin/steamos-select-branch" "/usr/bin/steamos-set-timezone" \
      "/usr/bin/steamos-update"
rm -rf "$POLKIT_LINKS_DIR"

# --- 4. System Restoration ---
info "Restoring gamescope capabilities..."
# Strip elevated capabilities from gamescope binary to return to system default
[[ -x /usr/bin/gamescope ]] && setcap -r /usr/bin/gamescope 2>/dev/null || true

echo -e "\n${YELLOW}--- Final System Choices ---${NC}"

# Choice A: Display Manager Restoration
# If the user used a Display Manager like SDDM, offer to re-enable it
if systemctl list-unit-files | grep -q sddm.service; then
    read -p "SDDM detected. Re-enable it for graphical login? (y/N): " dm_choice
    if [[ "$dm_choice" =~ ^[Yy]$ ]]; then
        systemctl enable sddm.service
        success "SDDM re-enabled."
    fi
fi

# Choice B: Personal Configuration Wipe
# Offer to remove per-user game settings and resolution profiles
if [[ -d "$CONFIG_DIR" ]]; then
    read -p "Remove user game configurations in $CONFIG_DIR? (y/N): " wipe_choice
    if [[ "$wipe_choice" =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        success "User configurations removed."
    else
        warn "User configurations preserved at $CONFIG_DIR."
    fi
fi

# --- 5. Finalize ---
# Reload systemd to apply all unit removals
systemctl daemon-reload
echo -e "\n${GREEN}Cleanup complete! System environment restored.${NC}"
