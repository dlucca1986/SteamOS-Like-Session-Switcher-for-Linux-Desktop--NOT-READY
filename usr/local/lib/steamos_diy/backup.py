#!/usr/bin/env python3
import os
import sys
import tarfile
import subprocess
from datetime import datetime
from pathlib import Path


def get_ssot():
    """Carica il SSoT direttamente dal file di configurazione."""
    conf = {
        'next_session': '/var/lib/steamos-diy/next_session',
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


def generate_links_recap():
    """Trova dinamicamente i link che puntano alla sorgente."""
    target_prefix = "/usr/local/lib/steamos_diy"
    recap_commands = [
        "#!/bin/bash\n",
        "# Script di ripristino automatico link simbolici\n",
        "echo 'Ripristino link simbolici in corso...'\n"
    ]

    try:
        cmd = [
            "find", "/usr", "-type", "l", "-lname", f"{target_prefix}*"
        ]
        links = subprocess.check_output(cmd, text=True).splitlines()

        for link_path in links:
            target = os.readlink(link_path)
            parent_dir = os.path.dirname(link_path)
            recap_commands.append(f"mkdir -p {parent_dir}\n")
            recap_commands.append(f"ln -sf {target} {link_path}\n")

    except subprocess.CalledProcessError as e:
        recap_commands.append(f"# Errore durante il discovery: {e}\n")

    return "".join(recap_commands)


def run_backup():
    """Esegue il backup chirurgico con ripristino intelligente dei link."""
    ssot = get_ssot()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Determina la cartella di backup basandosi sulla config utente
    user_config_path = Path(ssot.get('user_config')).parent
    backup_root = user_config_path / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    archive_name = backup_root / f"sdy_backup_{timestamp}.tar.gz"
    recap_file = backup_root / "restore_links.sh"

    # 1. Genera lo script di ripristino link
    links_script = generate_links_recap()
    with open(recap_file, "w") as f:
        f.write(links_script)

    # 2. Definisce cosa includere
    sources = [
        (ssot.get('next_session'), "system/next_session"),
        ("/etc/default/steamos_diy.conf", "system/steamos_diy.conf"),
        ("/usr/local/lib/steamos_diy", "source/steamos_diy"),
        (str(user_config_path), "user/config_steamos"),
        (str(recap_file), "restore_links.sh")
    ]

    print(f"📦 Creazione backup: {archive_name.name}...")

    try:
        with tarfile.open(archive_name, "w:gz") as tar:
            for src_path, arc_name in sources:
                if src_path and Path(src_path).exists():
                    # Evitiamo di includere i backup ricorsivamente
                    tar.add(
                        src_path,
                        arcname=arc_name,
                        filter=lambda t: None if "backups" in t.name else t
                    )
                    print(f"  + {src_path} -> OK")

        # Pulizia temporanei
        if recap_file.exists():
            recap_file.unlink()

        print("\n✅ Backup completato con successo!")
        print(f"📍 Destinazione: {archive_name}")

    except Exception as e:
        print(f"\n❌ ERRORE CRITICO: {e}")
        if archive_name.exists():
            archive_name.unlink()
        sys.exit(1)


if __name__ == "__main__":
    run_backup()
