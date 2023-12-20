#!/bin/bash

cd $(dirname "$BASH_SOURCE")
cd evalbase
kill -9 `cat huey.pid`
kill -9 `cat guni.pid`
