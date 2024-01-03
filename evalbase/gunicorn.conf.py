WSGI_APP = 'evalbase:application'
bind = f'unix:{__file__}/socket'
workers = 3
accesslog = 'access.log'
errorlog = 'error.log'
pidfile = 'gunicorn.pid'
loglevel = 'info'
daemon = True
