#!/bin/bash

# Note: Collabora repository with pending patches
# https://git.collabora.com/cgit/linux.git/log/?h=topic/chromeos/waiting-for-upstream

chromeos_path=$(python -c "from config import chromeos_path; print chromeos_path;")
chromeos_repo=$(python -c  "from config import chromeos_repo; print chromeos_repo;")

stable_path=$(python -c "from config import stable_path; print stable_path;")
stable_repo=$(python -c  "from config import stable_repo; print stable_repo;")

upstream_path=$(python -c "from config import upstream_path; print upstream_path;")
upstream_repo=$(python -c  "from config import upstream_repo; print upstream_repo;")

next_path=$(python -c "from config import next_path; print next_path;")
next_repo=$(python -c  "from config import next_repo; print next_repo;")

rebase_baseline_branch=$(python -c "from config import rebase_baseline_branch; print rebase_baseline_branch;")

android_baseline_branch=$(python -c "from config import android_baseline_branch; print android_baseline_branch;")
android_repo=$(python -c  "from config import android_repo; print android_repo;")
android_path=$(python -c "from config import android_path; print android_path;")

upstreamdb=$(python -c "from config import upstreamdb; print upstreamdb;")
nextdb=$(python -c "from config import nextdb; print nextdb;")

if [[ -d "${chromeos_path}" ]]; then
	pushd "${chromeos_path}"
	git fetch origin
	if git rev-parse --verify "${rebase_baseline_branch}" >/dev/null 2>&1; then
		git checkout "${rebase_baseline_branch}"
		git pull
	else
		git checkout -b "${rebase_baseline_branch}" "origin/${rebase_baseline_branch}"
	fi
	git remote -v | grep upstream || {
		git remote add upstream "${upstream_repo}"
	}
	git fetch upstream
	popd
else
	git clone "${chromeos_repo}" "${chromeos_path}"
	pushd "${chromeos_path}"
	git checkout -b "${rebase_baseline_branch}" "origin/${rebase_baseline_branch}"
	git remote add upstream "${upstream_repo}"
	git fetch upstream
	popd
fi

if [[ -d "${android_path}" ]]; then
	pushd "${android_path}"
	git fetch origin
	if git rev-parse --verify "${android_baseline_branch}" >/dev/null 2>&1; then
		git checkout "${android_baseline_branch}"
		git pull
	else
		git checkout -b "${android_baseline_branch}" "origin/${android_baseline_branch}"
	fi
	popd
else
	git clone "${android_repo}" "${android_path}"
	pushd "${android_path}"
	git checkout -b "${android_baseline_branch}" "origin/${android_baseline_branch}"
	git remote add upstream "${upstream_repo}"
	git fetch upstream	# for tags
	popd
fi

if [[ -d "${stable_path}" ]]; then
	pushd "${stable_path}"
	git pull
	popd
else
	git clone "${stable_repo}" "${stable_path}"
fi

echo "Initializing database"
python initdb.py

if [[ ! -e "${upstreamdb}" || "$1" = "-f" ]]; then
	echo "Initializing upstream database"
	if [[ -d "${upstream_path}" ]]; then
		pushd "${upstream_path}"
		git checkout master
		git pull
		popd
	else
		git clone "${upstream_repo}" "${upstream_path}"
	fi
	python initdb-upstream.py
fi

if [[ ! -e "${nextdb}" || "$1" = "-f" ]]; then
	echo "Initializing next database"
	if [[ -d "${next_path}" ]]; then
		pushd "${next_path}"
		git fetch origin
		git reset --hard origin/master
		popd
	else
		git clone "${next_repo}" "${next_path}"
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
