#!/bin/bash

source env/bin/activate
export HOST=$1

python -m flask run --host=0.0.0.0 &
