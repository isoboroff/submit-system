from .defaults import *
DEBUG = False
SECRET_KEY = 'NEED A REAL KEY HERE'
ALLOWED_HOSTS = ['127.0.0.1']
EMAIL_HOST = 'smtp.nist.gov'

# Authentication
# These are sandbox settings, change for production
LOGIN_GOV = {
    'discovery_uri': 'https://idp.int.identitysandbox.gov/.well-known/openid-configuration',
    'client_id': 'urn:gov:gsa:openidconnect.profiles:sp:sso:nist:bench2-sb',
    'redirect_uri': 'http://localhost:8000/login_gov_complete',
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
