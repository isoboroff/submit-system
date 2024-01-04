#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $SCRIPT_DIR
. venv/bin/activate
cd evalbase
nohup python manage.py run_huey > huey.log 2>&1 &
echo $! > huey.pid 
nohup uwsgi --ini uwsgi.ini > uwsgi.out 2>&1 &

