#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY
# VERSION:      1.0.0 - Python
# DESCRIPTION:  Compatibility shim for SteamOS OTA update infrastructure.
#               Returns Exit Code 0 to simulate a successful status.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/steamos_diy/helpers/jupiter-biosupdate.py
# LICENSE:      MIT
# =============================================================================

import sys
import subprocess


def main():
    """
    Intercept Jupiter BIOS update requests and report success.
    """
    # System logger configuration
    tag = "steamos-diy"
    msg = "[JUPITER-SHIM] Jupiter BIOS update request intercepted. Reporting: OK (Simulated)"

    # Send message to system logger (equivalent to: echo "..." | logger -t tag)
    subprocess.run(["logger", "-t", tag, msg], check=False)

    # Exit with success (0) to satisfy Steam Client requirements
    sys.exit(0)


if __name__ == "__main__":
    main()
