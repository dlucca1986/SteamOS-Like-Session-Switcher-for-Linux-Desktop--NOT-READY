#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY - Restore Tool
# VERSION:      1.0.0 - Python
# DESCRIPTION:  Full system restoration and dynamic symlink reconstruction.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# PATH:         /usr/local/lib/steamos_diy/restore.py
# =============================================================================

import os
import sys
import tarfile
import subprocess
from pathlib import Path

def check_root():
    if os.geteuid() != 0:
        print("❌ ERRORE: Questo script deve essere eseguito con sudo.")
        sys.exit(1)

def get_ssot():
    # Fallback identici al backup tool per coerenza
    conf = {
        'next_session': '/var/lib/steamos_diy/next_session',
        'user_config': '/home/lelo/.config/steamos_diy/config'
    }
    path = "/etc/default/steamos_diy.conf"
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    conf[k.strip()] = v.strip().strip('"').strip("'")
    return conf

def run_restore(archive_path):
    check_root()
    ssot = get_ssot()
    archive = Path(archive_path)

    if not archive.exists():
        print(f"❌ ERRORE: Archivio non trovato: {archive_path}")
        return

    print(f"📂 Ripristino da: {archive.name}...")

    # Mappatura inversa: Nome nel tar -> Path reale
    user_config_dir = Path(ssot.get('user_config')).parent
    
    mapping = {
        "system/next_session": ssot.get('next_session'),
        "system/steamos_diy.conf": "/etc/default/steamos_diy.conf",
        "source/steamos_diy": "/usr/local/lib/steamos_diy",
        "user/config_steamos": str(user_config_dir),
        "restore_links.sh": "/tmp/restore_links.sh"
    }

    try:
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name in mapping:
                    target = mapping[member.name]
                    # Crea le directory genitore se mancano
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    
                    # Estrazione manuale per gestire il cambio nome/percorso
                    member.name = os.path.basename(target)
                    tar.extract(member, path=os.path.dirname(target))
                    print(f"  + Ripristinato: {target}")

        # 2. Esecuzione script link simbolici
        recap_script = Path("/tmp/restore_links.sh")
        if recap_script.exists():
            print("🔗 Ricostruzione link simbolici...")
            os.chmod(recap_script, 0o755)
            subprocess.run([str(recap_script)], check=True)
            recap_script.unlink()

        print("\n✅ Ripristino completato con successo!")
        print("🔄 Si consiglia di riavviare la sessione.")

    except Exception as e:
        print(f"\n❌ ERRORE DURANTE IL RIPRISTINO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: sudo python3 restore.py /percorso/al/backup.tar.gz")
    else:
        run_restore(sys.argv[1])
