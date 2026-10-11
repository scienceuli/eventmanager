"""
Settings for the Docker deployment.

Everything that differs between deployments (secrets, hosts, database, mail)
comes from environment variables, which the Ansible role writes into the
container's env file. The application constants below mirror
local_settings.py - keep both in sync when changing them.
"""

import environ

from .base import *

env = environ.Env()

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
USE_2FA = env.bool("USE_2FA", default=False)

if USE_2FA:
    LOGIN_URL = "two_factor:login"

if DEBUG:
    GRAPPELLI_ADMIN_TITLE = "FOBI Eventmanager (DEVELOPMENT)"

# Public base URL, e.g. "https://einstein.science-and-more.com"
SITE_URL = env("SITE_URL").rstrip("/")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[SITE_URL])

# TLS is terminated by nginx on the host
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = SITE_URL.startswith("https")
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

# Database, e.g. postgres://user:password@db:5432/eventmanager
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# Files: static and public media are served by nginx on the host from
# bind-mounted directories. Private media (invoices, confirmations, ...) is
# kept outside MEDIA_ROOT so nginx can never serve it; django-private-storage
# serves it under /private-media/ after a permission check.
STATIC_ROOT = env("STATIC_ROOT", default="/data/static")
MEDIA_ROOT = env("MEDIA_ROOT", default="/data/media")
PRIVATE_STORAGE_ROOT = env("PRIVATE_STORAGE_ROOT", default="/data/private")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}

# Keys
MAPBOX_KEY = env("MAPBOX_KEY", default="")
ENCRYPT_KEY = env("ENCRYPT_KEY")
MAILGUN_API_KEY = env("MAILGUN_API_KEY", default="")
MAILGUN_URL = env("MAILGUN_URL", default="")

# email settings
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_FILE_PATH = env("EMAIL_FILE_PATH", default="/data/sent_emails")
DEFAULT_CHARSET = "utf-8"

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

DEFAULT_FROM_EMAIL = "anmeldung@vfll.de"
FT_FROM_EMAIL = "geschaeftsstelle@vfll.de"
REPLY_TO_EMAIL = "silke.leibner@vfll.de"
MV_REPLY_TO_EMAIL = "tagungsorganisation@vfll.de"
FT_REPLY_TO_EMAIL = "tagungsorganisation@vfll.de"
TESTING_GROUP = "ft_orga"

EVENT_RECEIVER_EMAIL = "fortbildung@vfll.de"
EMAIL_NOTIFY_BCC = []

# order and registration email settings
SEND_EMAIL_AFTER_ORDER_CREATION = False
SEND_EMAIL_AFTER_REGISTRATION_TO_MEMBER = True
SEND_EMAIL_AFTER_FT_REGISTRATION_TO_ADMIN = False
SEND_INVOICE_AFTER_ORDER_CREATION = False

# which event member listing is shown in frontend
EVENT_SHOWN_IN_FRONTEND = "2024-06-11_Willkommensveranstaltung"

# should registration date be shown in frontend
REGISTRATION_DATE_SHOWN_IN_EVENT_LIST = True

TOUR_LIMITS = {"I": 2, "II": 30}
WS_LIMITS = {"I": 20, "II": 20, "III": 15, "IV": 14, "V": 20, "VI": 1000}

# PAYPAL
PAYPAL_TEST = env.bool("PAYPAL_TEST", default=True)  # sandbox
PAYPAL_RECEIVER_EMAIL = env("PAYPAL_RECEIVER_EMAIL", default="")
PAYPAL_ENABLED = env.bool("PAYPAL_ENABLED", default=False)

# no double E-Mail allowed for members
NO_MEMBER_DUPLICATES_ALLOWED = True

# maintenance Mode
MAINTENANCE_MODE = env.bool("MAINTENANCE_MODE", default=False)
MAINTENANCE_BYPASS_QUERY = env("MAINTENANCE_BYPASS_QUERY", default="")
MAINTENANCE_END_DATE = env("MAINTENANCE_END_DATE", default="")

# event categories settings
SALON_CATEGORY = "veranstaltungsreihen"
MESSEN_CATEGORY = "messen"

PARTNER_CATEGORIES = ["fortbildungen_kooperation"]

# registration possible for these events even when registration not possible
# for category or event
EVENTS_WITH_REGISTRATION_POSSIBLE = ["ffl_mv_2024"]

# settings for order
ONE_ORDER_ONE_INVOICE = True
ORDER_DATE_DELAYED = False
ORDER_DATE_TIMEDELTA = 5  # the order date is the first_day of last event belonging to order minus this integer (days)

# api settings for Member Admin Api
TOKEN_URL = env("TOKEN_URL", default="")
MEMBER_ADMIN_URL = env("MEMBER_ADMIN_URL", default="")
MEMBER_ADMIN_USER_USERNAME = env("MEMBER_ADMIN_USER_USERNAME", default="")
MEMBER_ADMIN_USER_SECRET = env("MEMBER_ADMIN_USER_SECRET", default="")

# newsletter
NEWSLETTER_EMAIL_FROM = "fortbildung@vfll.de"
SHOW_NEWSLETTER_SIGNUP = True

# HEADLINE FOR ALL VFLL EVENT IN JOME VIEW
ALL_EVENTS_HEADLINE = "Alle VFLL-Fortbildungen auf einen Blick"

# mailqueue settings: mails are queued and sent by the "mailqueue" service
MAILQUEUE_QUEUE_UP = True
MAILQUEUE_CELERY = False
MAILQUEUE_STORAGE = True
MAILQUEUE_ATTACHMENT_DIR = "mailqueue-attachments"

# django-meta/SEO settings
META_SITE_PROTOCOL = SITE_URL.split("://")[0]
META_SITE_DOMAIN = SITE_URL.split("://")[1]
HOME_NAME = "VFLL Veranstaltungskalender"
HOME_TITLE = "VFLL Veranstaltungskalender"
HOME_TEXT = "Hier findet ihr die Veranstaltungen des VFLL."
DEFAULT_META_DESCRIPTION = "Eine interessante Fortbildungsveranstaltung des VFLL."
DEFAULT_META_KEYWORDS = ["Veranstaltungskalender", "Fortbildung", "VFLL"]

# mjml: TCP server runs as its own container
MJML_BACKEND_MODE = "tcpserver"
MJML_TCPSERVERS = [
    (env("MJML_HOST", default="mjml"), env.int("MJML_PORT", default=28101)),
]

# domain in emails
EMAIL_LINK_DOMAIN = SITE_URL
