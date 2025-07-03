#!/bin/sh
PID_FILE="$HOME/.var/app/com.gnome.dataguardian/config/daemon.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Stopping Data Guardian daemon (PID: $PID)..."
    kill "$PID"
else
    echo "Data Guardian daemon not running (no PID file found)."
fi