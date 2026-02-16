# --- BEGIN STEAMOS-DIY TRIGGER ---
# This block automatically starts the Game Mode session only on TTY1 
# and only if no other graphical display is already running.
if [[ -z $DISPLAY && $XDG_VTNR -eq 1 ]]; then
    LAUNCHER="/usr/bin/steamos-session-launch"
    
    if [[ -x "$LAUNCHER" ]]; then
        # Load global environment variables (SSOTH) if the config file exists
        [[ -f /etc/default/steamos_diy.conf ]] && . /etc/default/steamos_diy.conf
        
        # Execute the launcher and redirect all output (stdout/stderr) 
        # to the system log via journald (accessible via 'journalctl -t steamos-diy')
        exec "$LAUNCHER" > >(logger -t steamos-diy) 2>&1
    fi
fi

# Load the standard bashrc for interactive shell features
[[ -f ~/.bashrc ]] && . ~/.bashrc
# --- END STEAMOS-DIY TRIGGER ---
