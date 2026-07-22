"""Minimal Django settings for the nabokov live-demo API.

There is no database, no sessions, no templates: the landing page is a static
file served by Caddy; Django only answers ``POST /api/lint``.
"""

import os

from django.core.management.utils import get_random_secret_key

# No cookies are signed and nothing is encrypted, so a per-process random key
# is fine; set NABOKOV_SECRET_KEY to pin one anyway.
SECRET_KEY = os.environ.get("NABOKOV_SECRET_KEY") or get_random_secret_key()

DEBUG = os.environ.get("NABOKOV_DEBUG") == "1"

ALLOWED_HOSTS = [
    "nabokov.viewflow.io",
    "nabokov.lan",
    "localhost",
    "127.0.0.1",
    "testserver",  # django.test.Client
]

INSTALLED_APPS: list[str] = []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "nabokov_web.urls"
WSGI_APPLICATION = "nabokov_web.wsgi.application"

DATABASES: dict = {}

USE_TZ = True

# TLS terminates at viewflow.io's nginx; Caddy forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Lint payloads are small — reject anything bigger long before spaCy sees it.
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024
