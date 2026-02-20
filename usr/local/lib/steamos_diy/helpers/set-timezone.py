#!/usr/bin/env python3
"""
# =============================================================================
# PROJECT:      SteamMachine-DIY
# VERSION:      1.0.0 - Python
# DESCRIPTION:  Compatibility shim for SteamOS OTA update infrastructure.
#               Intercepts timezone change requests from Steam Client.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/steamos_diy/helpers/set-timezone.py
# LICENSE:      MIT
# =============================================================================
"""

# pylint: disable=invalid-name, duplicate-code

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# pylint: disable=invalid-name


def log_to_journal(tag, message):
    """
    Force message injection into systemd-journal.
    Ensures visibility in the Control Center.
    """
    full_msg = f"{tag}: {message}"
    try:
        subprocess.run(
            ["systemd-cat", "-t", tag],
            input=full_msg.encode("utf-8"),
            check=False,
        )
    except FileNotFoundError:
        print(full_msg, flush=True)


def get_log_file():
    """Extract log file path from SSoT or return a temporary fallback."""
    ssot_path = Path("/etc/default/steamos_diy.conf")
    if ssot_path.exists():
        try:
            with ssot_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if "LOG_FILE=" in line:
                        return (
                            line.split("=", 1)[1].strip().strip('"').strip("'")
                        )
        except OSError:
            pass
    return "/tmp/steamos-diy-fallback.log"


def main():
    """
    Handle timezone requests by logging via systemd-cat and physical file.
    """
    target_zone = sys.argv[1] if len(sys.argv) > 1 else "UTC"
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # TAG definition for Control Center color parsing
    tag = "BRANCH-SHIM"
    msg1 = f"Intercepting Steam Client timezone request: {target_zone}"
    msg2 = "Timezone request acknowledged. Host OS integrity preserved."

    # 1. JOURNAL LOGGING (For Control Center visibility)
    log_to_journal(tag, msg1)
    log_to_journal(tag, msg2)

    # 2. PHYSICAL FILE LOGGING (For persistence)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{tag}] {msg1}\n")
            f.write(f"[{timestamp}] [{tag}] {msg2}\n")
    except OSError:
        # If the log file is unwritable, do not block the shim execution.
        pass

    # 3. Exit 0 for Steam Client (Prevents UI error popups)
    sys.exit(0)


if __name__ == "__main__":
    main()
