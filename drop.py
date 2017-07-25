import sqlite3
import os
import subprocess
import re
from config import rebasedb, droplist

workdir = os.getcwd()

conn = sqlite3.connect(rebasedb)
# conn.text_factory = str

c = conn.cursor()
c2 = conn.cursor()

# Drop all Android patches. We'll pick them up from the most recent version.

c.execute("select sha, description from commits")
for (sha, desc) in c.fetchall():
    if desc.startswith('ANDROID:'):
	c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
	c2.execute("UPDATE commits SET reason=('android') where sha='%s'" % sha)
    if desc.startswith('android:'):
	c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
	c2.execute("UPDATE commits SET reason=('android') where sha='%s'" % sha)
    if desc.startswith('Android:'):
	c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
	c2.execute("UPDATE commits SET reason=('android') where sha='%s'" % sha)

conn.commit()

# Now drop commits touching directories/files specified in droplist.

c.execute("select sha from commits")
for (sha,) in c.fetchall():
    c.execute("select filename from files where sha is '%s'" % sha)
    for (filename,) in c.fetchall():
        dropped = 0
        for (dir, reason) in droplist:
	    if filename.startswith(dir):
		c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
	        c2.execute("UPDATE commits SET reason=('%s') where sha='%s'" % (reason, sha))
		dropped = 1
	        break
	if dropped:
	    break

conn.commit()

conn.close()

# c.execute('SELECT * FROM commits')
# c.fetchone() -> read one result
#
# for entry in c.execute(SELECT * FROM commits ORDER BY date'):
#     print entry
#     print entry.sha
#     print entry.description
