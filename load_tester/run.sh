#!/bin/bash

source env/bin/activate
export HOST=$1
export MONITOR_IP=10.1.1.1
export MONITOR_PORT=10444

python app.py &
