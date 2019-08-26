#!/bin/bash

if [ -z "$1" ]
then
	echo "Missing parameter (commit sha)"
	exit 1
fi

# if cherry-pick is clean, we have no conflict.
# Keep going, but alert user.
git cherry-pick $1 >/tmp/commit-log.$$ 2>&1
if [ $? -eq 0 ]
then
    echo "Expected conflict when rebasing $1, but got none. Please verify."
    echo "Commit log:"
    cat /tmp/commit-log.$$
    rm -f /tmp/commit-log.$$
    exit 1
fi

# abort if unhandled changes left
files=$(git rerere status)
if [ -n "${files}" ]
then
    echo "Unresolved conflicts: ${files}, please fix"
    rm -f /tmp/commit-log.$$
    exit 1
fi

# Prepare to tweak commit log to indicate conflicts

git show -s --format=%B $1 > /tmp/commit-msg.$$
echo "Conflicts:" >> /tmp/commit-msg.$$

git status --porcelain --untracked-files=no > /tmp/filelist.$$

# tag unmerged files to be ready for commit
while read line
do
    s=$(echo ${line} | awk '{print $1}')
    f=$(echo ${line} | awk '{print $2}')
    case "$s" in
    DD)
	echo "	$f" >> /tmp/commit-msg.$$
        git rm $f
	;;
    UU|AA)
	echo "	$f" >> /tmp/commit-msg.$$
        git add $f
	;;
    UD|DU|AU|UA)
        echo "State '$s' for $f not handled, please address manually"
        exit 1
	;;
    *)
	;;
    esac
done < /tmp/filelist.$$

# Ensure that image still builds
# echo "Running test build"
# make allmodconfig >/dev/null
# make -j80 >/dev/null 2>make.x86.log
# if [ $? -ne 0 ]
# then
#     echo "Build errors reported in make.x86.log, please fix"
#     rm -f /tmp/commit-log.$$
#     exit 1
# fi

echo "
[rebase49(groeck): Resolved conflicts]
Signed-off-by: Guenter Roeck <groeck@chromium.org>" >> /tmp/commit-msg.$$
git commit -F /tmp/commit-msg.$$

rm -f /tmp/commit-msg.$$ /tmp/commit-log.$$ /tmp/filelist.$$
