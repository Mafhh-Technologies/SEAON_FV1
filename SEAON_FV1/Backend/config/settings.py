from pathlib import Path
import os

BASE_DIR=Path(__file__).resolve().parent.parent

# Lightweight .env loader so Windows users do not need an extra dependency.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))
SECRET_KEY="seaon-dev-secret-change-in-production"
DEBUG=True
ALLOWED_HOSTS=["127.0.0.1","localhost"]
INSTALLED_APPS=[
 "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
 "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
 "corsheaders","rest_framework","erp"]
MIDDLEWARE=[
 "corsheaders.middleware.CorsMiddleware","django.middleware.security.SecurityMiddleware",
 "django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware",
 "django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware",
 "django.contrib.messages.middleware.MessageMiddleware"]
ROOT_URLCONF="config.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"public"],
 "APP_DIRS":True,"OPTIONS":{"context_processors":[
 "django.template.context_processors.request","django.contrib.auth.context_processors.auth",
 "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION="config.wsgi.application"; ASGI_APPLICATION="config.asgi.application"
DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"seaon.db"}}
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE="en-us"; TIME_ZONE="Asia/Kolkata"; USE_I18N=True; USE_TZ=True
STATIC_URL="/static/"; STATIC_ROOT=BASE_DIR/"staticfiles"
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
CORS_ALLOW_ALL_ORIGINS=True
REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES":["erp.authentication.JWTAuthentication"],
 "DEFAULT_PERMISSION_CLASSES":["rest_framework.permissions.IsAuthenticated"]}

# Email notification settings (configure in Backend/.env).
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() in ("1", "true", "yes")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
EMAIL_TIMEOUT = 12
