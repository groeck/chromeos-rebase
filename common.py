import os
import sqlite3

workdir = os.getcwd()
dbdir = workdir + '/database'
upstreamdb = dbdir + '/upstream.db'
nextdb = dbdir + '/next.db'

def stabledb(version):
  return dbdir + "/stable-" + version + '.db'

def chromeosdb(version):
  return dbdir + "/chromeos-" + version + '.db'

def stable_branch(version):
    return "linux-%s.y" % version

def chromeos_branch(version):
    return "chromeos-%s" % version

def doremove(file):
  '''
  remove file if it exists
  '''

  try:
    os.remove(file)
  except OSError:
    pass

def createdb(db, op):
  '''
  remove and recreate database
  '''

  dbdir = os.path.dirname(db)
  if not os.path.exists(dbdir):
    os.mkdir(dbdir)

  doremove(db)

  conn = sqlite3.connect(db)
  c = conn.cursor()

  op(c)

  # Convention: table 'tip' ref 1 contains the most recently processed SHA.
  # Use this to avoid re-processing SHAs already in the database.
  c.execute("CREATE TABLE tip (ref integer, sha text)")
  c.execute("INSERT INTO tip (ref, sha) VALUES (?, ?)",
                  (1, ""))

  # Save (commit) the changes
  conn.commit()
  conn.close()
