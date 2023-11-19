#!/bin/sh
echo $RADICALE_USER:$RADICALE_PASSWORD > /radicale/users
printenv > /etc/environment
cron -f
