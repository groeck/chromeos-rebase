import os
import sqlite3
import subprocess

from config import chromeos_path, rebase_baseline_branch

workdir = os.getcwd()
dbdir = workdir + '/database'
upstreamdb = dbdir + '/upstream.db'
nextdb = dbdir + '/next.db'

def stable_baseline():
  '''
  Return most recent label in to-be-rebased branch
  '''

  currdir=os.getcwd()
  os.chdir(workdir+'/'+chromeos_path)
  tag=subprocess.check_output(['git', 'describe', rebase_baseline_branch])
  os.chdir(currdir)
  return tag.split('-')[0]

def rebase_baseline():
  '''
  Return most recent label in to-be-rebased branch
  '''

  baseline=stable_baseline()
  return baseline.split('.')[0]+'.'+baseline.split('.')[1]

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
