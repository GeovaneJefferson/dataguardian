#!/bin/bash

# Get the user's home directory
user_home="$HOME"
CONFIG_DIR="$user_home/.var/app/com.gnome.dataguardian/config"

# Find the PID file dynamically within the config directory
PID_FILE=$(find "$CONFIG_DIR" -type f -name "*.pid" -print -quit)

# Check if a PID file was found and exists
if [ -n "$PID_FILE" ] && [ -f "$PID_FILE" ]; then
    echo "Removing PID file: $PID_FILE"
    rm "$PID_FILE"  # Remove the PID file
else
    echo "No PID file found."
fi
