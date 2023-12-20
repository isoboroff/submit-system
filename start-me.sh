#!/bin/bash

cd $(dirname "$BASH_SOURCE")
. venv/bin/activate

cd evalbase
nohup python manage.py run_huey > huey.log 2>&1 &
echo $! > huey.pid
nohup gunicorn evalbase.wsgi > guni.log 2>&1 &
echo $! > guni.pid
