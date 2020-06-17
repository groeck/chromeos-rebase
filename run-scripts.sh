#!/bin/bash

progdir="$(dirname $0)"

cd "${progdir}"
./setup.sh
./genspreadsheet.py
./genstats.py
