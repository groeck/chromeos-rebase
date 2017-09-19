#!/bin/bash

# Note: Collabora repository with pending patches
# https://git.collabora.com/cgit/linux.git/log/?h=topic/chromeos/waiting-for-upstream

android_path=$(python -c "from config import android_path; print android_path;")
stable_path=$(python -c "from config import stable_path; print stable_path;")
upstream_path=$(python -c "from config import upstream_path; print upstream_path;")
next_path=$(python -c "from config import next_path; print next_path;")

rebase_baseline_branch=$(python -c "from config import rebase_baseline_branch; print rebase_baseline_branch;")
android_baseline_branch=$(python -c "from config import android_baseline_branch; print android_baseline_branch;")

upstreamdb=$(python -c "from config import upstreamdb; print upstreamdb;")
nextdb=$(python -c "from config import nextdb; print nextdb;")

if [ -d ${android_path} ]
then
	pushd ${android_path}
	git checkout ${android_baseline_branch}
	git pull
	popd
else
	git clone https://android.googlesource.com/kernel/common ${android_path}
	pushd ${android_path}
	git checkout -b ${android_baseline_branch} origin/${android_baseline_branch}
	git remote add upstream git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
	git fetch upstream	# for tags
	popd
fi

if [ -d ${stable_path} ]
then
	pushd ${stable_path}
	git pull
	popd
else
	git clone git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git ${stable_path}
fi

echo "Initializing database"
python initdb.py

if [ ! -e ${upstreamdb} -o "$1" = "-f" ]
then
	echo "Initializing upstream database"
	if [ -d ${upstream_path} ]
	then
		pushd ${upstream_path}
		git checkout master
		git pull
		popd
	else
		git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git ${upstream_path}
	fi
	python initdb-upstream.py
fi

if [ ! -e ${nextdb} -o "$1" = "-f" ]
then
	echo "Initializing next database"
	if [ -d ${next_path} ]
	then
		pushd ${next_path}
		git fetch origin
		git reset --hard origin/master
		popd
	else
		git clone git://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git ${next_path}
	fi
	python initdb-next.py
fi

echo "Calculating initial drop list"
python drop.py
echo "Calculating initial revert list"
python revertlist.py
echo "Calculating replace list"
python upstream.py
echo "Calculating topics"
python topics.py
