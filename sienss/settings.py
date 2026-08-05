"""
Django settings for sienss project.

Fonctionne en deux modes, sans rien changer au code :
- En local, sans variables d'environnement définies : SQLite, DEBUG=True,
  exactement comme avant (aucune installation supplémentaire nécessaire).
- En production, avec les variables d'environnement définies (voir
  .env.example) : PostgreSQL via DATABASE_URL, DEBUG=False, sécurité HTTPS
  activée, fichiers statiques servis par WhiteNoise.
"""

from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent


# --- Sécurité --------------------------------------------------------------
# SECRET_KEY : en local, une valeur par défaut est utilisée (peu importe,
# ce n'est pas un vrai secret). En production, définissez SECRET_KEY dans
# l'environnement avec une valeur générée aléatoirement (voir .env.example).
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure--%@#ba^ozl1kh339oi_doj+eh%403l=wdo8#a=u=s-kywpff*v",
)

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1,testserver", cast=Csv()
)

# En production (DEBUG=False), on force les cookies et redirections HTTPS.
# Les données de santé ne doivent jamais transiter en clair (Chapitre 4.4).
if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 jours
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Nécessaire derrière un proxy HTTPS (Railway, Render, etc.)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# --- Applications ------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

# Modèle utilisateur personnalisé (Chapitre 5.1) — à déclarer AVANT toute
# migration, car Django ne permet pas de changer ce paramètre après coup
# sans opérations manuelles lourdes sur la base.
AUTH_USER_MODEL = 'core.Utilisateur'

LOGIN_URL = 'connexion'
LOGIN_REDIRECT_URL = 'tableau_bord'
LOGOUT_REDIRECT_URL = 'connexion'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # sert les fichiers statiques en production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sienss.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.citation_du_jour',
            ],
        },
    },
]

WSGI_APPLICATION = 'sienss.wsgi.application'


# --- Base de données ---------------------------------------------------------
# Si DATABASE_URL est définie dans l'environnement (Railway/Render la
# fournissent automatiquement pour une base PostgreSQL), elle est utilisée.
# Sinon, repli sur SQLite pour le développement local (Chapitre 9).

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


# --- Validation des mots de passe --------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internationalisation -----------------------------------------------------
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Porto-Novo'
USE_I18N = True
USE_TZ = True


# --- Fichiers statiques (CSS, JavaScript, images) -----------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # utilisé par collectstatic en production
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- E-mail (réinitialisation de mot de passe, Chapitre 3.1) -----------------
# En développement (aucune variable EMAIL_HOST définie) : les e-mails sont
# affichés dans la console plutôt qu'envoyés réellement — pratique pour
# tester le lien de réinitialisation sans vrai serveur mail.
# En production : définissez EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
# (ex. via un service comme SendGrid, Mailgun, ou le SMTP de votre hébergeur).
EMAIL_HOST = config("EMAIL_HOST", default="")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
    EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@sienss.local")
