#!/bin/bash

if [ -z "$1" ]
then
	exit 1
fi

# Get old commit message and tweak it to indicate squash

git show -s --format=%B HEAD > /tmp/commit-msg.$$
msg=$(git show --format=%s -s $1)
echo "[rebase49(groeck): Squash with
	'${msg}']
Signed-off-by: Guenter Roeck <groeck@chromium.org>" >> /tmp/commit-msg.$$

git cherry-pick --no-commit $1
if [ $? -ne 0 ]
then
    exit 1
fi

git commit --amend -F /tmp/commit-msg.$$

rm -f /tmp/commit-msg.$$
