#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

kill -9 `cat $SCRIPT_DIR/evalbase/uwsgi.pid`
kill -9 `cat $SCRIPT_DIR/evalbase/huey.pid`
kill -9 `cat $SCRIPT_DIR/evalbase/ikat-validator.pid`
