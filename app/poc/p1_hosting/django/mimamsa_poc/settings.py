"""Mimamsa P1 hosting PoC: Django (ASGI) settings. No ORM models; raw SQL through a psycopg async pool."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("MIMAMSA_SECRET_KEY", "poc-insecure-dev-key-not-for-production")
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
INSTALLED_APPS = []
MIDDLEWARE = ["mimamsa_poc.views.AuthStubMiddleware"]
ROOT_URLCONF = "mimamsa_poc.urls"
ASGI_APPLICATION = "mimamsa_poc.asgi.application"
WSGI_APPLICATION = "mimamsa_poc.wsgi.application"
DATABASES = {}  # the ORM is unused in this PoC; see views.POOL
USE_TZ = True
MIMAMSA_DB = os.environ.get("MIMAMSA_DB", "host=127.0.0.1 port=55432 user=poc dbname=poc")
MIMAMSA_PDF_ROOT = Path(os.environ.get("MIMAMSA_PDF_ROOT", BASE_DIR / "pdfstore")).resolve()
MIMAMSA_DEV_TOKEN = os.environ.get("MIMAMSA_DEV_TOKEN", "dev-token")
MIMAMSA_POOL_MAX = int(os.environ.get("MIMAMSA_POOL_MAX", "8"))
LOGGING = {"version": 1, "disable_existing_loggers": False, "root": {"level": "WARNING"}}
