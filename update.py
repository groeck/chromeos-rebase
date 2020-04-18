# -*- coding: utf-8 -*-"
import sqlite3
import os
import re
from config import rebasedb
from common import upstreamdb, nextdb

subject = re.compile("(ANDROID: *|CHROMIUM: *|CHROMEOS: *|UPSTREAM: *|FROMGIT: *|FROMLIST: *|BACKPORT: *)*(.*)")

def findsha(uconn, sha, desc):
  '''
  Try to find matching SHA in provided database.
  Return updated SHA, or None if not found.
  '''

  c = uconn.cursor()

  c.execute("select sha from commits where sha is '%s'" % sha)
  usha = c.fetchone()
  if usha:
    # print "  Found SHA %s in upstream database" % usha
    return sha

  # The SHA is not upstream, or not known at all.
  # See if we can find the commit subject;

  s = subject.search(desc)
  if s:
    sdesc = s.group(2).replace("'", "''")
    c.execute("select sha from commits where subject is '%s'" % sdesc)
    usha = c.fetchone()
    if usha:
      print "  Found upstream SHA '%s'" % usha
      return usha[0]

  return None

def update_commits():
  '''
  Validate 'usha' field in rebase database.
  Verify if the upstream SHA actually exists by looking it up in the upstream
  database. If it doesn't exist, and if a matching commit is not found either,
  remove it.
  '''

  conn = sqlite3.connect(rebasedb)
  uconn = sqlite3.connect(upstreamdb)
  nconn = sqlite3.connect(nextdb) if nextdb else None
  c = conn.cursor()

  c.execute("select sha, usha, subject from commits where usha != ''")
  for (sha, usha, desc) in c.fetchall():
    uusha = findsha(uconn, usha, desc)
    # if it is not in the upstream database, maybe it is in -next.
    # Try to pick it up from there.
    if uusha is None and nconn:
      uusha = findsha(nconn, usha, desc)
    if usha != uusha:
      if not uusha:
        uusha = ""
      print "SHA '%s': Updating usha '%s' with '%s'" % (sha, usha, uusha)
      c.execute("UPDATE commits set usha='%s' where sha='%s'" % (uusha, sha))

  conn.commit()
  conn.close()
  uconn.close()
  if nconn:
      nconn.close()

update_commits()
