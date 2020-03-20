import os
import re
import sqlite3
import subprocess
from config import upstream_path
from common import rebase_baseline, workdir, upstreamdb, createdb, rebase_target_tag

def mktables(c):
  ''' Create tables '''
  c.execute("CREATE TABLE commits (sha text, subject text, in_baseline integer)")
  c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")

  c.execute("CREATE TABLE files (sha text, filename text)")
  c.execute("CREATE INDEX file_sha ON files (sha)")
  c.execute("CREATE INDEX file_name ON files (filename)")

def handle(c, range, baseline):
  commits = subprocess.check_output(['git', 'log', '--abbrev=12', '--oneline', '--no-merges', '--reverse', range])
  for commit in commits.splitlines():
    if commit != "":
      elem = commit.split(" ", 1)
      sha = elem[0]
      last = sha
      subject = elem[1].rstrip('\n')
      subject = subject.decode('latin-1') if isinstance(subject, str) else subject
      c.execute("INSERT INTO commits(sha, subject, in_baseline) VALUES (?, ?, ?)",
                (sha, subject, baseline,))
      filenames = subprocess.check_output(['git', 'show', '--name-only', '--format=', sha])
      for fn in filenames.splitlines():
        if fn != "":
          c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha, fn))

    if last:
      c.execute("UPDATE tip set sha='%s' where ref=1" % last)

def update_baseline(c):
  c.execute("select sha from commits where in_baseline is 0")
  for (sha) in c.fetchall():
    try:
      subprocess.check_output(['git', 'merge-base', '--is-ancestor', sha, rebase_baseline()])
      c.execute("UPDATE commits SET in_baseline=1 where sha='%s'" % sha)
    except:
      pass

def update_upstreamdb():
  start = rebase_baseline()

  try:
    # see if we previously handled anything. If yes, use it.
    # Otherwise re-create database.
    conn = sqlite3.connect(upstreamdb)
    c = conn.cursor()
    c.execute("select sha from tip")
    sha = c.fetchone()
    conn.close()
    if sha and sha[0] != "":
      start = sha[0]
      # In this case, the baseline may have changed. Assume that it only
      # moves forward. Update database to reflect new baseline.
      update_baseline(c, start, rebase_baseline())
    else:
      fail
  except:
    createdb(upstreamdb, mktables)

  os.chdir(upstream_path)

  upstream_drop = start + '..' + rebase_target_tag()
  upstream_pick = rebase_target_tag() + '..'

  conn = sqlite3.connect(upstreamdb)
  c = conn.cursor()

  handle(c, upstream_drop, 1)
  handle(c, upstream_pick, 0)

  conn.commit()
  conn.close()

  os.chdir(workdir)

if __name__ == "__main__":
  update_upstreamdb()
