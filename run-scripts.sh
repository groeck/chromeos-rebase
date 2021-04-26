#!/bin/bash

progdir="$(dirname $0)"
logfile="/tmp/run-scripts.$(date +%F).log"

# IT loves uninstalling stuff, so just force a reinstall
pip3 install google_auth_oauthlib >/dev/null 2>&1

cd "${progdir}"
./setup.sh > "${logfile}" 2>&1
./genspreadsheet.py >> "${logfile}" 2>&1
./genstats.py >> "${logfile}" 2>&1
