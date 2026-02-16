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
    subprocess.run(["logger", "-t", "steamos-diy", f"[LAUNCHER] {msg}"], check=False)

def run():
    # 1. Carica SSoT
    conf = {}
    with open("/etc/default/steamos_diy", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().strip('"').strip("'")

    # 2. Configura l'ambiente una sola volta (Calibrato)
    # Applichiamo solo le variabili specifiche del Desktop Environment
    for k, v in conf.items():
        if k.startswith(("XDG_", "KDE_")):
            os.environ[k] = v

    while True:
        # 3. Leggi il target
        try:
            with open(conf['next_session'], "r") as f:
                target = f.read().strip()
        except:
            target = "steam"

        # 4. Esecuzione e Switch (Anti-Loop)
        if target == "steam":
            log_msg("Avvio STEAM (Game Mode)...")
            cmd = [conf['bin_gs'], "-e", "-f", "--", conf['bin_steam'], "-gamepadui", "-steamos3"]
            subprocess.run(cmd)
            next_val = "desktop"
        else:
            log_msg("Avvio DESKTOP (Plasma)...")
            subprocess.run([conf['bin_plasma']])
            next_val = "steam"

        # 5. Scrittura atomica per il prossimo boot/crash
        tmp = f"{conf['next_session']}.tmp"
        with open(tmp, "w") as f:
            f.write(next_val)
        os.replace(tmp, conf['next_session'])
        
        time.sleep(0.5)

if __name__ == "__main__":
    run()
