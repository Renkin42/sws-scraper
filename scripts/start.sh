#!/bin/sh
cron
tail -f /var/log/cron.log
echo $RADICALE_USER:$RADICALE_PASSWORD > /radicale/users
python3 -m radicale --config /radicale/config
python3 /scripts/scraper.py
