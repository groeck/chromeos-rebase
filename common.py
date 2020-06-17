import os
import re
import sqlite3
import subprocess

from config import upstream_path, chromeos_path, rebase_baseline_branch, rebase_target
from config import next_repo

workdir = os.getcwd()
dbdir = workdir + '/database'
upstreamdb = dbdir + '/upstream.db'
nextdb = dbdir + '/next.db' if next_repo else None

def stable_baseline():
  '''
  Return most recent label in to-be-rebased branch
  '''

  currdir=os.getcwd()
  os.chdir(workdir+'/'+chromeos_path)
  tag=subprocess.check_output(['git', 'describe', rebase_baseline_branch]).decode()
  os.chdir(currdir)
  return tag.split('-')[0]

def rebase_baseline():
  '''
  Return most recent label in to-be-rebased branch
  '''

  baseline=stable_baseline()
  return baseline.split('.')[0]+'.'+baseline.split('.')[1]

version=re.compile("(v[0-9]+(\.[0-9]+)(-rc[0-9]+)?)\s*")

def rebase_target_tag():
  '''
  Return most recent label in upstream kernel
  '''

  if rebase_target == 'latest':
    currdir=os.getcwd()
    os.chdir(workdir+'/'+upstream_path)
    tag=subprocess.check_output(['git', 'describe'])
    os.chdir(currdir)
    v=version.match(tag)
    if v:
      tag=v.group(0).strip('\n')
    else:
      tag="HEAD"
  else:
    tag=rebase_target

  return tag

def rebase_target_version():
  return rebase_target_tag().strip('v')

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
