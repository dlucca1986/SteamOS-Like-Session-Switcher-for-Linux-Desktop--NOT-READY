#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY
# VERSION:      1.0.0 - Python
# DESCRIPTION:  Compatibility shim for SteamOS OTA update infrastructure.
#               Returns Exit Code 7 to simulate an "Up to Date" status.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/steamos_diy/helpers/steamos-update.py
# LICENSE:      MIT
# =============================================================================

import sys
import subprocess


def main():
    """
    Intercepts Steam OTA requests and reports an 'Up to Date' status.
    """
    # 1. Tag and Message Configuration
    tag = "steamos-diy"
    msg1 = "[UPDATE-SHIM] Steam OTA update request intercepted."
    msg2 = "[UPDATE-SHIM] Reporting status: UP TO DATE (Forced Exit 7)."

    # 2. Logging to System Journal (for Control Center visibility)
    # Using subprocess to communicate with system logger
    subprocess.run(["logger", "-t", tag, msg1], check=False)
    subprocess.run(["logger", "-t", tag, msg2], check=False)

    # 3. Exit Code 7: The specific signal telling Steam there are no updates
    sys.exit(7)


if __name__ == "__main__":
    main()
