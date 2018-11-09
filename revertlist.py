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

c.execute("select date, sha, disposition, description from commits")
for (date, sha, disposition, desc) in c.fetchall():
  # If the patch is already dropped, don't bother any further
  if disposition == "drop":
    continue
  m = rp.search(desc)
  if m:
    ndesc = m.group(1)
    print("Found revert : '%s' (%s)" % (desc.replace("'", "''"), sha))
    ndesc = ndesc.replace("'", "''")
    c2.execute("select date, sha from commits where description is '%s'"
               % ndesc)
    # Search for matching original commit. Only revert its first occurrance,
    # and only if its date is older than the revert.
    fsha = c2.fetchone()
    if fsha:
      if date > fsha[0]:
        # print("    Matching commit : %s" % fsha[1])
        print("    Marking %s for drop" % fsha[1])
        c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'"
                   % fsha[1])
        c2.execute("UPDATE commits SET reason=('reverted') where sha='%s'"
                   % fsha[1])
        c2.execute("UPDATE commits SET updated=('%d') where sha='%s'" % (NOW(), sha))
      else:
        print("    Matching commit later than reverse")
    else:
      print("    No matching commit found")
    # Hmmm .. the below seems redundant ad drops everything.
    print("    Marking %s for drop" % sha)
    c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
    c2.execute("UPDATE commits SET reason=('reverted') where sha='%s'" % sha)
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
#     print entry.description
