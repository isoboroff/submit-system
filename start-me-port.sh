#!/bin/bash

cd $(dirname "$BASH_SOURCE")
. venv/bin/activate

cd evalbase
nohup python manage.py run_huey > huey.log 2>&1 &
echo $! > huey.pid
gunicorn --bind 127.0.0.1:5000 evalbase.wsgi
