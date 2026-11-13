#!/bin/sh
# Sends mails queued by django-mail-queue (MAILQUEUE_QUEUE_UP = True).
# Replaces the cron job of the old server.
# Also runs daily housekeeping (purge of unconfirmed newsletter subscriptions).
set -e

last_daily=0

while true; do
    python manage.py send_queued_messages || echo "send_queued_messages failed" >&2

    now=$(date +%s)
    if [ $((now - last_daily)) -ge 86400 ]; then
        python manage.py purge_unconfirmed_subscriptions \
            || echo "purge_unconfirmed_subscriptions failed" >&2
        last_daily=$now
    fi

    sleep "${MAILQUEUE_INTERVAL:-60}"
done
