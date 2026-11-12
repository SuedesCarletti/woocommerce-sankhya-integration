#!/bin/bash
export PYTHONUNBUFFERED=1
export HOST=0.0.0.0
export PORT=${PORT:-3000}

pip3 install --user -r requirements.txt

~/.local/bin/gunicorn \
    --worker-tmp-dir /dev/shm \
    --workers 2 \
    --threads 4 \
    --worker-class=gthread \
    --bind 0.0.0.0:$PORT \
    app:app
