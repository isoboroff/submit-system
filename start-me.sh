#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $SCRIPT_DIR
. venv/bin/activate
cd evalbase

cd checkers/check-ikat
nohup python passage_validator_servicer.py files/ikat_2023_passages_hashes.sqlite3 > ../../ikat-validator.log 2>&1 &
echo $! > ../../ikat-validator.pid
cd ../..

nohup python manage.py run_huey > huey.log 2>&1 &
echo $! > huey.pid 
nohup uwsgi --ini uwsgi.ini > uwsgi.out 2>&1 &

