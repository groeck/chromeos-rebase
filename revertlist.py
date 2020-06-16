# -*- coding: utf-8 -*-"
from __future__ import print_function
import sqlite3
import os
import re
import time
from config import rebasedb

def NOW():
  return int(time.time())

workdir = os.getcwd()

conn = sqlite3.connect(rebasedb)
# conn.text_factory = str

c = conn.cursor()
c2 = conn.cursor()

rp = re.compile('Revert "(.*)"')

# date:
#         git show --format="%ct" -s ${sha}
# subject:
#        git show --format="%s" -s ${sha}
# file list:
#        git show --name-only --format="" ${sha}

# Insert a row of data
# c.execute("INSERT INTO commits VALUES (1489758183,sha,subject)")
# c.execute("INSERT INTO files VALUES (sha,filename)")
# sha and filename must be in ' '

c.execute("select date, sha, disposition, subject from commits")
for (committed, sha, disposition, desc) in c.fetchall():
  # If the patch has already been dropped, don't bother any further
  if disposition == "drop":
    continue
  m = rp.search(desc)
  if m:
    ndesc = m.group(1)
    print("Found revert : '%s' (%s)" % (desc.replace("'", "''"), sha))
    ndesc = ndesc.replace("'", "''")
    c2.execute("select committed, sha from commits where subject is '%s'"
               % ndesc)
    # Search for commit closest to the revert in the past
    # (There may be multiple if the revert was repeated)
    revert_committed = None
    revert_sha = None
    for (_committed, _sha,) in c2.fetchall():
      if _committed < committed:
        if not revert_sha or revert_committed < _committed:
          revert_committed = _committed
          revert_sha = _sha

    if revert_sha:
      print("    Marking %s for drop" % revert_sha)
      c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'"
                 % revert_sha)
      c2.execute("UPDATE commits SET reason=('reverted') where sha='%s'"
                 % revert_sha)
      c2.execute("UPDATE commits SET dsha='%s' where sha='%s'"
                 % (sha, revert_sha))
      c2.execute("UPDATE commits SET updated=('%d') where sha='%s'" % (NOW(), revert_sha))
    else:
      print("    No matching commit found")
    print("    Marking %s for drop" % sha)
    c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
    c2.execute("UPDATE commits SET reason=('reverted') where sha='%s'" % sha)
    if revert_sha:
      c2.execute("UPDATE commits SET dsha='%s' where sha='%s'" % (revert_sha, sha))
    c2.execute("UPDATE commits SET updated=('%d') where sha='%s'" % (NOW(), sha))

conn.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
conn.close()

# c.execute('SELECT * FROM commits')
# c.fetchone() -> read one result
#
# for entry in c.execute(SELECT * FROM commits ORDER BY date'):
#     print entry
#     print entry.sha
#     print entry.subject
