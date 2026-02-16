#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY - Session Launcher
# VERSION:      1.0.0 - Phyton
# DESCRIPTION:  Core Session Manager with Dynamic Gamescope Mapping.
#               Handles seamless transitions between Steam and Desktop.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/steamos_diy/session_launch.py
# =============================================================================

import os
import time
import subprocess


def log_msg(msg):
    """Invia un messaggio al journal di sistema per il Control Center."""
    subprocess.run(["logger", "-t", "steamos-diy", f"[LAUNCHER] {msg}"],
                   check=False)


def run():
    # 1. Carica SSoT
    conf = {}
    ssot_path = "/etc/default/steamos_diy.conf"
    with open(ssot_path, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                val = v.strip().strip('"').strip("'")
                key = k.strip()
                conf[key] = val
                # Iniezione automatica variabili d'ambiente
                os.environ[key] = val

    # 2. Ciclo infinito di sessione
    while True:
        try:
            with open(conf['next_session'], "r") as f:
                target = f.read().strip()
        except (FileNotFoundError, KeyError):
            target = "steam"

        if target == "steam":
            log_msg("Avvio sessione STEAM (Game Mode).")
            # Comando pulito usando i binari dal SSoT
            cmd = [
                conf['bin_gs'], "-e", "-f", "--",
                conf['bin_steam'], "-gamepadui", "-steamos3"
            ]
            subprocess.run(cmd)
            log_msg("Sessione Steam terminata. Switch a Desktop impostato.")
            next_val = "desktop"
        else:
            log_msg("Avvio sessione DESKTOP (Plasma).")
            # Avvio Plasma usando il binario dal SSoT
            subprocess.run([conf['bin_plasma']])
            log_msg("Sessione Desktop terminata. Switch a Steam impostato.")
            next_val = "steam"

        # 3. Scrittura atomica
        next_session_file = conf['next_session']
        tmp = f"{next_session_file}.tmp"
        with open(tmp, "w") as f:
            f.write(next_val)
        os.replace(tmp, next_session_file)

        time.sleep(0.5)


if __name__ == "__main__":
    run()
