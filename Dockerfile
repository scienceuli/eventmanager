# Bookworm, not trixie: trixie no longer ships wkhtmltopdf (admin event PDF).
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=eventmanager.container_settings

# Runtime libraries: wkhtmltopdf (django-wkhtmltopdf), fonts for PDF
# rendering, gettext for compilemessages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wkhtmltopdf \
        fonts-dejavu-core \
        gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements.txt is compiled from requirements.in for this exact platform
# (Python 3.13, x86_64 Linux): every compiled package comes as a wheel, so no
# compiler is needed here.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The app user owns /app because events/views.py writes eventmanager.log
# into the working directory at import time.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data \
    && chown -R app:app /app /data
USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "eventmanager.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]
