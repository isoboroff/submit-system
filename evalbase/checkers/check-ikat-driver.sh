#!/bin/bash

RUN_HOME=`pwd`
SCRIPT_HOME=$(dirname $(readlink -f $0))

. $SCRIPT_HOME/../../venv/bin/activate

cd $SCRIPT_HOME/check-ikat
python3 main.py -f files $RUN_HOME/$1
exit $!
