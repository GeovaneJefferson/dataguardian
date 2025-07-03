#!/bin/sh
# Start the Data Guardian daemon
# exec python3 /app/share/dataguardian/src/main.py

#!/bin/sh
# Start the Data Guardian daemon
exec python3 /app/share/dataguardian/src/main.py
export PYTHONPATH=/app/share/dataguardian
exec python3 -m src.main