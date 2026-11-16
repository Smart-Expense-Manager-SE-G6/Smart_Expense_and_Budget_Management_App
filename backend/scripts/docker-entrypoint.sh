#!/bin/sh
# Production entrypoint (S3-10). Starts as root only to give the unprivileged
# "app" user its two writable folders, then runs the command as "app".
#
# The receipts volume is shared with the backup service, which runs as root, so
# a fresh volume or a restore can leave it owned by root. Fixing ownership on
# every start keeps receipt uploads working whatever touched the volume last.
set -eu
chown -R app:app /app/private_media /app/staticfiles
exec setpriv --reuid=app --regid=app --init-groups "$@"
