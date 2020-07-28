#!/usr/bin/env python3
# -*- coding: utf-8 -*-"
'''Generate database with commits which are in -next but not in mainline.
'''

from __future__ import print_function
import sqlite3
import os
import subprocess
from config import next_path
from common import workdir, nextdb, createdb, rebase_target_tag


def mktables(c):
  # Create tables
  c.execute("CREATE TABLE commits (committed timestamp, sha text, patchid text, subject text)")
  c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")
  c.execute("CREATE INDEX patchid ON commits (patchid)")

  c.execute("CREATE TABLE files (sha text, filename text)")
  c.execute("CREATE INDEX file_sha ON files (sha)")
  c.execute("CREATE INDEX file_name ON files (filename)")


def handle(c):
  next_pick = rebase_target_tag() + '..'

  cmd = ['git', 'log', '--abbrev=12', '--format=%ct %h %s', '--no-merges', '--reverse', next_pick]
  commits = subprocess.check_output(cmd, encoding='utf-8', errors='ignore')
  for commit in commits.splitlines():
    if commit != '':
      elem = commit.split(' ', 2)
      timestamp = elem[0]
      sha = elem[1]
      subject = elem[2].rstrip()

      ps = subprocess.Popen(['git', 'show', sha], stdout=subprocess.PIPE)
      spid = subprocess.check_output(['git', 'patch-id'], stdin=ps.stdout, encoding='utf-8', errors='ignore')
      patchid = spid.split(' ', 1)[0]

      c.execute("INSERT INTO commits(committed, sha, patchid, subject) VALUES (?, ?, ?, ?)",
                (timestamp, sha, patchid, subject))
      filenames = subprocess.check_output(['git', 'show', '--name-only',
                                           '--format=', sha])
      for fn in filenames.splitlines():
        if fn != "":
          c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha, fn))


def initdb_next():
  # Always re-create the 'next' database.
  # Its SHAs are unstable and thus can not be relied on.
  createdb(nextdb, mktables)
  os.chdir(next_path)
  conn = sqlite3.connect(nextdb)
  c = conn.cursor()
  handle(c)
  conn.commit()
  conn.close()
  os.chdir(workdir)


if __name__ == "__main__":
  initdb_next()
