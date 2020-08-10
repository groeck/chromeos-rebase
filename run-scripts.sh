#!/bin/bash

progdir="$(dirname $0)"
logfile="/tmp/run-scripts.$(date +%F).log"

cd "${progdir}"
./setup.sh > "${logfile}" 2>&1
./genspreadsheet.py >> "${logfile}" 2>&1
./genstats.py >> "${logfile}" 2>&1
