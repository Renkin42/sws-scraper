#!/bin/sh
echo $RADICALE_USER:$RADICALE_PASSWORD > /radicale/users
python3 -m radicale --config /radicale/config
