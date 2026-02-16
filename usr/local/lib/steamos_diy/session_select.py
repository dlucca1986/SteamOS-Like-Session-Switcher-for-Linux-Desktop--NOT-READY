#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY - Session Switcher (Trigger)
# VERSION:      1.0.0
# DESCRIPTION:  Dispatcher to trigger session switches between Steam and KDE.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/steamos_diy/session_select.py
# LICENSE:      MIT
# =============================================================================

import os
import sys
import subprocess


def log_msg(msg):
    """Sends a message to the system journal."""
    subprocess.run(
        ["logger", "-t", "steamos-diy", f"[SELECT] {msg}"],
        check=False
    )


def select():
    """Main logic for atomic session switching and shutdown."""
    if len(sys.argv) < 2:
        return

    # 1. Load SSoT (Single Source of Truth)
    conf = {}
    try:
        with open("/etc/default/steamos_diy.conf", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    conf[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        # Fallback if config doesn't exist yet
        conf['next_session'] = "/var/lib/steamos_diy/next_session"

    # 2. Target Validation and Normalization
    target = sys.argv[1].lower()
    if target == "plasma":
        target = "desktop"

    if target not in ["desktop", "steam"]:
        log_msg(f"Target '{target}' not recognized.")
        return

    log_msg(f"Switching to: {target.upper()}")

    # 3. Atomic Write (Prevents corruption on power loss)
    next_session_path = conf.get(
        'next_session',
        '/var/lib/steamos_diy/next_session'
    )
    tmp = f"{next_session_path}.tmp"
    with open(tmp, "w") as f:
        f.write(target)
    os.replace(tmp, next_session_path)

    # 4. Current Session Shutdown
    if target == "desktop":
        log_msg("Closing Steam...")
        steam_bin = conf.get('bin_steam', 'steam')
        subprocess.run([steam_bin, "-shutdown"], stderr=subprocess.DEVNULL)
    else:
        log_msg("KDE Logout...")
        for cmd in ["qdbus6", "qdbus"]:
            try:
                # Use try/except to avoid crash if the binary is missing
                args = ["org.kde.Shutdown", "/Shutdown", "logout"]
                subprocess.run([cmd] + args, stderr=subprocess.DEVNULL)
                break
            except FileNotFoundError:
                continue


if __name__ == "__main__":
    select()
