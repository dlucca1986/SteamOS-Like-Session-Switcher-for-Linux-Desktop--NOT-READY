#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY - Restore Tool
# VERSION:      1.1.0 - Python
# DESCRIPTION:  Full system restoration and dynamic symlink reconstruction.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/steamos_diy/restore.py
# LICENSE:      MIT
# =============================================================================

import os
import sys
import tarfile
import subprocess
from pathlib import Path


def check_root():
    """Ensures the script is running with root privileges."""
    if os.geteuid() != 0:
        print("❌ ERROR: This script must be run with sudo.")
        sys.exit(1)


def get_ssot():
    """Loads SSoT configuration for consistent restoration paths."""
    conf = {
        'next_session': '/var/lib/steamos_diy/next_session',
        'user': os.environ.get('SUDO_USER') or os.environ.get('USER')
    }
    path = "/etc/default/steamos_diy.conf"
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    conf[k.strip()] = v.strip().strip('"').strip("'")

    # Fallback home path
    if 'user' in conf and not conf.get('user_home'):
        conf['user_home'] = f"/home/{conf['user']}"

    return conf


def run_restore(archive_path):
    """Performs the restoration from a compressed tarball."""
    check_root()
    ssot = get_ssot()
    archive = Path(archive_path)

    if not archive.exists():
        print(f"❌ ERROR: Archive not found: {archive_path}")
        return

    print(f"📂 Restoring from: {archive.name}...")

    # Inverse mapping: Name in tar -> Real system path
    user_home = Path(ssot.get('user_home', '/root'))
    user_config_dir = Path(ssot.get('user_config',
                           user_home / ".config/steamos_diy/config")).parent

    mapping = {
        "system/next_session": ssot.get('next_session'),
        "system/steamos_diy.conf": "/etc/default/steamos_diy.conf",
        "source/steamos_diy": "/usr/local/lib/steamos_diy",
        "user/config_steamos": str(user_config_dir),
        "user/bash_profile": str(user_home / ".bash_profile"),
        "restore_links.sh": "/tmp/restore_links.sh"
    }

    try:
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name in mapping:
                    target = mapping[member.name]
                    # Create parent directories if missing
                    os.makedirs(os.path.dirname(target), exist_ok=True)

                    # Manual extraction to handle path/name mapping
                    member.name = os.path.basename(target)
                    tar.extract(member, path=os.path.dirname(target))
                    print(f"  + Restored: {target}")

        # 2. Symlink reconstruction script execution
        recap_script = Path("/tmp/restore_links.sh")
        if recap_script.exists():
            print("🔗 Reconstructing symbolic links...")
            os.chmod(recap_script, 0o755)
            subprocess.run([str(recap_script)], check=True)
            recap_script.unlink()

        print("\n✅ Restoration completed successfully!")
        print("🔄 A system reboot or session restart is recommended.")

    except Exception as e:
        print(f"\n❌ ERROR DURING RESTORATION: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sudo python3 restore.py /path/to/backup.tar.gz")
    else:
        run_restore(sys.argv[1])
