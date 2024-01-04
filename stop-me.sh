#!/bin/bash
kill -9 `cat uwsgi.pid`
kill -9 `cat huey.pid`
