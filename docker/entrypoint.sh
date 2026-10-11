#!/bin/sh
# Container entrypoint. The web service sets RUN_MIGRATIONS=1, so schema
# migrations and collectstatic run once per start there and not again in
# helper services (mailqueue) that share the same image.
set -e

mkdir -p "${STATIC_ROOT:-/data/static}" "${MEDIA_ROOT:-/data/media}" "${PRIVATE_STORAGE_ROOT:-/data/private}"
# Static and media are served by nginx on the host, private files are not
chmod 750 "${PRIVATE_STORAGE_ROOT:-/data/private}"

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput --verbosity 0
fi

exec "$@"
