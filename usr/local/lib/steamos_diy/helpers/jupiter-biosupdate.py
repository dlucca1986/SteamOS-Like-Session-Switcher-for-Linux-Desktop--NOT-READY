#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY
# VERSION:      1.0.0 - Python
# DESCRIPTION:  Compatibility shim for SteamOS OTA update infrastructure.
#               Returns Exit Code 7 to simulate an "Up to Date" status.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/helpers/jupiter-biosupdate.py
# LICENSE:      MIT
# =============================================================================

import sys
import subprocess


def main():
    # Messaggio per il Control Center
    tag = "steamos-diy"
    msg = "[JUPITER-SHIM] Richiesta BIOS Jupiter intercettata. Reporting: OK (Simulato)"

    # Invio al logger di sistema
    # Equivale a: echo "..." | logger -t steamos-diy
    subprocess.run(["logger", "-t", tag, msg], check=False)

    # Uscita con successo (0) per Steam
    sys.exit(0)


if __name__ == "__main__":
    main()
  
