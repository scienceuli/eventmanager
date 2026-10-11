#!/bin/sh
# Sends mails queued by django-mail-queue (MAILQUEUE_QUEUE_UP = True).
# Replaces the cron job of the old server.
set -e

while true; do
    python manage.py send_queued_messages || echo "send_queued_messages failed" >&2
    sleep "${MAILQUEUE_INTERVAL:-60}"
done
