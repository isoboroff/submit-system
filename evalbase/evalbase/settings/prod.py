from .defaults import *
DEBUG = False
SECRET_KEY = '3$cui8i8l@+r5@!qawwdf1pm0jbg!-y)mnef-9n@$!w^2(14jn'
ALLOWED_HOSTS = ['129.6.101.59']
EMAIL_HOST = 'smtp.nist.gov'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': '/raids/ir1/submit-system/my.cnf',
        },
    }
}
