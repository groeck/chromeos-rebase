import os
import re
import sqlite3
import subprocess
from config import upstreamdb, upstream_path, rebase_baseline, rebase_target

upstream_drop = rebase_baseline + '..' + rebase_target
upstream_pick = rebase_target + '..'

workdir = os.getcwd()

try:
    os.remove(upstreamdb)
except:
    pass

conn = sqlite3.connect(upstreamdb)

c = conn.cursor()
c2 = conn.cursor()

# Create tables
c.execute("CREATE TABLE commits (sha text, subject text, in_baseline integer)")
c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")

c.execute("CREATE TABLE files (sha text, filename text)")
c.execute("CREATE INDEX file_sha ON files (sha)")
c.execute("CREATE INDEX file_name ON files (filename)")

conn.commit()

os.chdir(upstream_path)

def handle(range, baseline):
    commits = subprocess.check_output(['git', 'log', '--abbrev=12', '--oneline', '--no-merges', '--reverse', range])
    for commit in commits.splitlines():
      if commit != "":
        elem = commit.split(" ", 1)
        sha = elem[0]
        subject = elem[1].rstrip('\n')
        subject = subject.decode('latin-1') if isinstance(subject, str) else subject
        c.execute("INSERT INTO commits(sha, subject, in_baseline) VALUES (?, ?, ?)",
                  (sha, subject, baseline,))
        filenames = subprocess.check_output(['git', 'show', '--name-only', '--format=', sha])
        for fn in filenames.splitlines():
          if fn != "":
            c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha, fn))

    conn.commit()

handle(upstream_drop, 1)
handle(upstream_pick, 0)

conn.close()
