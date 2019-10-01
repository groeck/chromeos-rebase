# -*- coding: utf-8 -*-"
'''Generate database with commits which are in -next but not in mainline.
'''

from __future__ import print_function
import sqlite3
import os
import subprocess
from config import next_path, rebase_target
from common import workdir, nextdb, createdb

def mktables(c):
  # Create tables
  c.execute("CREATE TABLE commits (sha text, subject text, in_baseline integer)")
  c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")

  c.execute("CREATE TABLE files (sha text, filename text)")
  c.execute("CREATE INDEX file_sha ON files (sha)")
  c.execute("CREATE INDEX file_name ON files (filename)")

def handle(c):
  next_pick = rebase_target + '..'
  commits = subprocess.check_output(['git', 'log', '--oneline', '--no-merges',
                                    next_pick])
  for commit in commits.splitlines():
    if commit != "":
      elem = commit.split(" ", 1)
      sha = elem[0]
      subject = elem[1].rstrip('\n')
      subject = subject.decode('latin-1') \
          if isinstance(subject, str) else subject
      c.execute("INSERT INTO commits(sha, subject, in_baseline) VALUES (?, ?, ?)",
                (sha, subject, 0,))
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
