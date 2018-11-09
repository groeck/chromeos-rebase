# -*- coding: utf-8 -*-"
from __future__ import print_function
import sqlite3
import os
import time
from config import rebasedb, subject_droplist, droplist

def NOW():
  return int(time.time())

def do_drop(c, sha, reason):
  c.execute("select disposition from commits where sha is '%s'" % sha)
  found = c.fetchone()
  if found[0] != "drop":
    print("Dropping SHA %s: %s" % (sha, reason))
    c.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
    c.execute("UPDATE commits SET reason=('%s') where sha='%s'" % (reason, sha))
    c.execute("UPDATE commits SET updated=('%d') where sha='%s'" % (NOW(), sha))

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
      do_drop(c2, sha, "android")

conn.commit()

# Now drop commits touching directories/files specified in droplist.

c.execute("select sha from commits")
for (_sha,) in c.fetchall():
  c.execute("select filename from files where sha is '%s'" % _sha)
  for (filename,) in c.fetchall():
    dropped = 0
    for (_dir, _reason) in droplist:
      if filename.startswith(_dir):
        do_drop(c2, _sha, _reason)
        dropped = 1
        break
    if dropped:
      break

conn.commit()

# Try again. This time drop duplicates.

dsha = []

c.execute("select sha,patchid,disposition from commits")
for (_sha,_patchid,_disposition,) in c.fetchall():
  if _disposition is 'drop':
    continue
  if _sha in dsha:
    continue
  c2.execute("select sha from commits where patchid is '%s'" % _patchid)
  for (__sha,) in c2.fetchall():
    if __sha in dsha:
      continue
    if _sha != __sha:
      do_drop(c2, __sha, "duplicate")
      dsha.append(__sha)

conn.commit()

conn.close()

# c.execute('SELECT * FROM commits')
# c.fetchone() -> read one result
#
# for entry in c.execute(SELECT * FROM commits ORDER BY date'):
#     print entry
#     print entry.sha
#     print entry.description
