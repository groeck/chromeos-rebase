#!/bin/bash

sha=$1
resolution=$2
reason=$3

# TODO: Check if sha is in database, and if parameters are correct

sqlite3 drop49.db "insert into droplist (sha, resolution, reason)
                   values ('${sha}', '${resolution}', '${reason}');"
