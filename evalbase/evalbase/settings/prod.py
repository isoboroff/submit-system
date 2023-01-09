from .defaults import *
DEBUG = False
SECRET_KEY = 'NEED A REAL KEY HERE'
ALLOWED_HOSTS = ['127.0.0.1']
EMAIL_HOST = 'smtp.nist.gov'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': '/raids/ir1/submit-system/my.cnf',
        },
    }
}
