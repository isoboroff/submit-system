#!/bin/bash
. venv/bin/activate
cd evalbase
nohup python manage.py run_huey > huey.log 2>&1 &
echo $! > huey.pid 
nohup uwsgi --http localhost:5000 --py-auto-reload --ini uwsgi.ini > uwsgi.out 2>&1 &

