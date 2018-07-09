# -*- coding: utf-8 -*-"
from __future__ import print_function
import sqlite3
import os
from config import rebasedb, subject_droplist, droplist

workdir = os.getcwd()

conn = sqlite3.connect(rebasedb)
# conn.text_factory = str

c = conn.cursor()
c2 = conn.cursor()

# Drop all Android patches. We'll pick them up from the most recent version.

c.execute("select sha, description from commits")
for (sha, desc) in c.fetchall():
  for prefix in subject_droplist:
    if desc.startswith(prefix):
      c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'"
                 % sha)
      c2.execute("UPDATE commits SET reason=('android') where sha='%s'"
                 % sha)

conn.commit()

# Now drop commits touching directories/files specified in droplist.

c.execute("select sha from commits")
for (_sha,) in c.fetchall():
  c.execute("select filename from files where sha is '%s'" % _sha)
  for (filename,) in c.fetchall():
    dropped = 0
    for (_dir, _reason) in droplist:
      if filename.startswith(_dir):
        c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'"
                   % _sha)
        c2.execute("UPDATE commits SET reason=('%s') where sha='%s'"
                   % (_reason, _sha))
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
