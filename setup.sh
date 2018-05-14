#!/bin/bash

# Note: Collabora repository with pending patches
# https://git.collabora.com/cgit/linux.git/log/?h=topic/chromeos/waiting-for-upstream

chromeos_path=$(python -c "from config import chromeos_path; print chromeos_path;")
chromeos_repo=$(python -c  "from config import chromeos_repo; print chromeos_repo;")

stable_path=$(python -c "from config import stable_path; print stable_path;")
stable_repo=$(python -c  "from config import stable_repo; print stable_repo;")

upstream_path=$(python -c "from config import upstream_path; print upstream_path;")
if [[ "$(dirname ${upstream_path})" = "." ]]; then
	# Needs to be an absolute path name
	upstream_path="$(pwd)/${upstream_path}"
fi
upstream_repo=$(python -c  "from config import upstream_repo; print upstream_repo;")

next_path=$(python -c "from config import next_path; print next_path;")
next_repo=$(python -c  "from config import next_repo; print next_repo;")

rebase_baseline_branch=$(python -c "from config import rebase_baseline_branch; print rebase_baseline_branch;")

android_baseline_branch=$(python -c "from config import android_baseline_branch; print android_baseline_branch;")
android_repo=$(python -c  "from config import android_repo; print android_repo;")
android_path=$(python -c "from config import android_path; print android_path;")

upstreamdb=$(python -c "from config import upstreamdb; print upstreamdb;")
nextdb=$(python -c "from config import nextdb; print nextdb;")

# Simple clone:
# Clone repository, do not add 'upstream' remote
clone_simple()
{
    local destdir=$1
    local repository=$2

    if [[ -d "${destdir}" ]]; then
	pushd "${destdir}"
	git checkout master
	git pull
	popd
    else
	git clone "${repository}" "${destdir}"
    fi
}

clone_simple "${upstream_path}" "${upstream_repo}"
clone_simple "${stable_path}" "${stable_repo}"

# Complex clone:
# Clone repository, check out branch, add 'upstream' remote
clone_complex()
{
    local destdir=$1
    local repository=$2
    local branch=$3

    if [[ -d "${destdir}" ]]; then
	pushd "${destdir}"
	git fetch origin
	if git rev-parse --verify "${branch}" >/dev/null 2>&1; then
		git checkout "${branch}"
		git pull
	else
		git checkout -b "${branch}" "origin/${branch}"
	fi
	git remote -v | grep upstream || {
		git remote add upstream "${upstream_path}"
	}
	git fetch upstream
	popd
    else
	git clone "${repository}" "${destdir}"
	pushd "${destdir}"
	git checkout -b "${branch}" "origin/${branch}"
	git remote add upstream "${upstream_path}"
	git fetch upstream
	popd
    fi
}

clone_complex "${chromeos_path}" "${chromeos_repo}" "${rebase_baseline_branch}"
clone_complex "${android_path}" "${android_repo}" "${android_baseline_branch}"
clone_complex "${next_path}" "${next_repo}" "master"

echo "Initializing database"
python initdb.py

if [[ ! -e "${upstreamdb}" || "$1" = "-f" ]]; then
	echo "Initializing upstream database"
	python initdb-upstream.py
fi

if [[ ! -e "${nextdb}" || "$1" = "-f" ]]; then
	echo "Initializing next database"
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
