# VFLL Eventmanager

Django 4.2 application for the VFLL event calendar (Veranstaltungskalender):
events, registrations, orders/invoices, newsletter, mailings and reports.

There are two ways to run it locally:

1. **Development setup** (Python venv + SQLite) – the usual way to work on the code.
2. **Docker Compose** (Postgres + gunicorn) – a smoke test of the container
   setup used on the servers.

---

## 1. Development setup

### Prerequisites

- Python 3.13 (the lock file `requirements.txt` is compiled for 3.13)
- Node.js + npm (Tailwind CSS build)
- Optional, depending on what you work on:
  - [`wkhtmltopdf`](https://wkhtmltopdf.org/) – PDF export of events in the admin
    (`brew install --cask wkhtmltopdf`)
  - an MJML TCP server – rendering of MJML e-mail templates
    (see [MJML server](#mjml-server-for-e-mail-templates))

### Install

```sh
cd eventmanager

python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt     # requirements.txt + black, isort, coverage

npm install
```

### Settings

`manage.py` uses `eventmanager.local_settings` by default. That file is
**git-ignored**, so it has to be created in `eventmanager/local_settings.py`
(ask a maintainer for the current version). It imports `eventmanager/base.py`,
uses the SQLite database `db-dev.sqlite3`, writes outgoing e-mails to the
`sent_emails/` directory and reads secrets from `eventmanager/.env`.

Create `eventmanager/.env` (also git-ignored) with these keys:

```ini
DEBUG=True
SECRET_KEY=some-long-random-string
USE_2FA=False

MAPBOX_KEY=
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPT_KEY=

MOODLE_SECRET=
MOODLE_URL=
MOODLE_ENDPOINT=

EMAIL_HOST=localhost
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_PORT=587
EMAIL_USE_TLS=True

MEMBER_ADMIN_USER_USERNAME=
MEMBER_ADMIN_USER_SECRET=

INVOICE_NINJA_BASE_URL=
INVOICE_NINJA_API_KEY=

MAILGUN_API_KEY=
MAILGUN_URL=
```

All keys read by `local_settings.py` must be present, even if they are empty.
External services (Moodle, Mailgun, Invoice Ninja, member admin API) are only
needed for the features that use them.

### Database

```sh
python manage.py migrate
python manage.py createsuperuser
```

### Run

Use two terminals:

```sh
# Terminal 1: rebuild Tailwind CSS on change
# (writes fobi_theme/static/css/output.css, which is not in git)
npm run dev

# Terminal 2: Django dev server
python manage.py runserver
```

Then open:

- Frontend: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>

`django-browser-reload` reloads the page automatically when templates or CSS
change.

### E-mails

With the file-based e-mail backend, mails are not sent but written to
`sent_emails/`. Mails queued by `django-mail-queue` are processed with:

```sh
python manage.py send_queued_messages
```

### MJML server (for e-mail templates)

`local_settings.py` expects an MJML TCP server on `127.0.0.1:28101`. The easiest
way is Docker:

```sh
docker run --rm -p 28101:28101 liminspace/mjml-tcpserver:1.4
```

### Tests and code style

```sh
python manage.py test

coverage run manage.py test && coverage html   # report in htmlcov/

black . && isort .
```

---

## 2. Docker Compose (container smoke test)

Runs the app the way it runs on the servers: gunicorn, Postgres 16, an MJML
server and a mail-queue worker, using `eventmanager.container_settings`
(all configuration via environment variables).

```sh
cd eventmanager
cp docker/env.example docker/.env   # fill in at least SECRET_KEY and ENCRYPT_KEY
docker compose up --build
```

On start the `web` service runs `migrate` and `collectstatic`
(`docker/entrypoint.sh`). Create an admin user with:

```sh
docker compose exec web python manage.py createsuperuser
```

The app is reachable at <http://localhost:8000>. Static and media files are
served by nginx on the servers, so locally only the app itself is reachable
(pages may appear without CSS).

---

## Dependencies

Direct dependencies are listed in `requirements.in`; `requirements.txt` is the
full lock file. To change dependencies, edit `requirements.in` and recompile:

```sh
uv pip compile requirements.in -o requirements.txt \
    --python-version 3.13 --python-platform x86_64-manylinux_2_28 \
    --annotation-style line
```
