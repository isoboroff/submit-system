from .defaults import *
import requests

DEBUG = False
SECRET_KEY = 'NEED A REAL KEY HERE'
ALLOWED_HOSTS = ['127.0.0.1']
EMAIL_HOST = 'smtp.nist.gov'

# Authentication
# These are sandbox settings, change for production
LOGIN_GOV = {
    'discovery_uri': 'https://secure.login.gov/.well-known/openid-configuration',
    'client_id': 'urn:gov:gsa:openidconnect.profiles:sp:sso:nist:bench2',
    'redirect_uri': 'https://ir.nist.gov/evalbase/accounts/login_gov_complete',
}

OPENID = requests.get(LOGIN_GOV['discovery_uri']).json()


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': '/raids/ir1/submit-system/my.cnf',
        },
    }
}
