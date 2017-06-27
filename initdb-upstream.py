import sqlite3
import os
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

# Create tables
c.execute("CREATE TABLE commits (sha text, description text, in_49 integer)")
c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")

c.execute("CREATE TABLE files (sha text, filename text)")
c.execute("CREATE INDEX file_sha ON files (sha)")
c.execute("CREATE INDEX file_name ON files (filename)")

conn.commit()

os.chdir(upstream_path)

commits = subprocess.check_output(['git', 'log', '--oneline', '--no-merges', upstream_drop])
for commit in commits.splitlines():
    if commit != "":
        elem = commit.split(" ", 1)
        sha = elem[0]
        description = elem[1].rstrip('\n')
	description = description.decode('latin-1') if isinstance(description, str) else description
	c.execute("INSERT INTO commits(sha, description, in_49) VALUES (?, ?, ?)", (sha, description,1,))
	filenames = subprocess.check_output(['git', 'show', '--name-only', '--format=', sha])
	for fn in filenames.splitlines():
	    if fn != "":
		c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha,fn))

conn.commit()

commits = subprocess.check_output(['git', 'log', '--oneline', '--no-merges', upstream_pick])
for commit in commits.splitlines():
    if commit != "":
        elem = commit.split(" ", 1)
        sha = elem[0]
        description = elem[1].rstrip('\n')
	description = description.decode('latin-1') if isinstance(description, str) else description
	c.execute("INSERT INTO commits(sha, description, in_49) VALUES (?, ?, ?)", (sha, description,0,))
	filenames = subprocess.check_output(['git', 'show', '--name-only', '--format=', sha])
	for fn in filenames.splitlines():
	    if fn != "":
		c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha,fn))

conn.commit()
conn.close()
