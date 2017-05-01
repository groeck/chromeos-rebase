#!/bin/bash

if [ -d linux-chrome ]
then
	pushd linux-chrome
	git checkout chromeos-4.4
	git pull
	popd
else
	git clone https://chromium.googlesource.com/chromiumos/third_party/kernel linux-chrome
	pushd linux-chrome
	git checkout -b chromeos-4.4 origin/chromeos-4.4
	popd
fi

if [ -d linux-android ]
then
	pushd linux-android
	git checkout android-4.4
	git pull
	popd
else
	git clone https://android.googlesource.com/kernel/common linux-android
	pushd linux-android
	git checkout -b android-4.4 origin/android-4.4
	git remote add upstream git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
	git fetch upstream	# for tags
	popd
fi

if [ -d linux-stable ]
then
	pushd linux-stable
	git pull
	popd
else
	git clone git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git linux-stable
fi

echo "Initializing database"
python initdb.py

if [ ! -e upstream49.db -o "$1" = "-f" ]
then
	echo "Initializing upstream database"
	if [ -d linux-upstream ]
	then
		pushd linux-upstream
		git checkout master
		git pull
		popd
	else
		git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git linux-upstream
	fi
	python initdb-upstream.py
fi

echo "Calculating initial drop list"
python drop.py
echo "Calculating initial revert list"
python revertlist.py
echo "Calculating replace list"
python upstream.py
echo "Calculating topics"
python topics.py
