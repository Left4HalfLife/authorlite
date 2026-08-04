#!/bin/sh
set -eu

mkdir -p /app/data
chown -R authorlite:authorlite /app/data
chmod -R a+rwX /app/data

exec su -s /bin/sh authorlite -c "$*"