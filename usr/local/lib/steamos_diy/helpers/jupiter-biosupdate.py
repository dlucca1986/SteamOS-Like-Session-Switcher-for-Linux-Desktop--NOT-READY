#!/usr/bin/env python3
"""
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
"""

# pylint: disable=invalid-name, duplicate-code

import subprocess
import sys


def log_to_journal(tag, message):
    """Force message injection into systemd-journal."""
    full_msg = f"{tag}: {message}"
    try:
        subprocess.run(
            ["systemd-cat", "-t", tag],
            input=full_msg.encode("utf-8"),
            check=False,
        )
    except FileNotFoundError:
        print(full_msg, flush=True)


def main():
    """Simulate successful BIOS update."""
    tag = "BRANCH-SHIM"
    msg = "Jupiter BIOS update intercepted. Reporting: OK (Simulated)"

    log_to_journal(tag, msg)
    sys.exit(0)


if __name__ == "__main__":
    main()
