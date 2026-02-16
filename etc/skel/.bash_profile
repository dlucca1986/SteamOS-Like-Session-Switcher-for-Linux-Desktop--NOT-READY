# --- BEGIN STEAMOS-DIY TRIGGER ---
# Questo blocco avvia la sessione Game Mode solo su TTY1 e se non c'è già un'interfaccia grafica.
if [[ -z $DISPLAY && $XDG_VTNR -eq 1 ]]; then
    LAUNCHER="/usr/bin/steamos-session-launch"
    if [[ -x "$LAUNCHER" ]]; then
        # Carica le variabili globali (SSOTH) se il file esiste
        [[ -f /etc/default/steamos_diy.conf ]] && . /etc/default/steamos_diy.conf
        
        # Avvia il launcher reindirizzando l'output al log di sistema (journald)
        exec "$LAUNCHER" > >(logger -t steamos-diy) 2>&1
    fi
fi

# Carica il bashrc standard se presente
[[ -f ~/.bashrc ]] && . ~/.bashrc
# --- END STEAMOS-DIY TRIGGER ---
