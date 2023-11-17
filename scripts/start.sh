#!/bin/sh
set -e
echo "Running Command 1"
echo $RADICALE_USER:$RADICALE_PASSWORD > /radicale/users
echo "Running Command 2"
python3 -m radicale --config /radicale/config
echo "Running Command 3"
python3 /scripts/test.py
