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

try:
    from subprocess import DEVNULL # py3k
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')


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
  Return most recent tag in to-be-rebased branch
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
    try:
      tag=subprocess.check_output(['git', 'describe'], encoding='utf-8')
    except TypeError: # py2
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


# match "vX.Y[.Z][.rcN]"
version = re.compile(r'(v[0-9]+(?:\.[0-9]+)+(?:-rc[0-9]+)?)\s*')

def get_integrated_tag(sha):
    """For a given SHA, find the first tag that includes it."""

    try:
        cmd = ['git', 'describe', '--match', 'v*', '--contains', sha]
        tag = subprocess.check_output(cmd, stderr=DEVNULL)
        return version.match(tag).group()
    except AttributeError:
        return None
    except subprocess.CalledProcessError:
        return None


# extract_numerics matches numeric parts of a Linux version as separate elements
# For example, "v5.4" matches "5" and "4", and "v5.4.12" matches "5", "4", and "12"
extract_numerics = re.compile(r'(?:v)?([0-9]+)\.([0-9]+)(?:\.([0-9]+))?(?:-rc([0-9]+))?\s*')

def version_to_number(version):
    """Convert Linux version to numeric value usable for comparisons.

    A branch with higher version number will return a larger number.
    Supports version numbers up to 999, and release candidates up to 99.

    Returns 0 if the kernel version can not be extracted.
    """

    m = extract_numerics.match(version)
    if m:
        major = int(m.group(1))
        minor1 = int(m.group(2))
        minor2 = int(m.group(3)) if m.group(3) else 0
        minor3 = int(m.group(4)) if m.group(4) else 0
        total = major * 1000000000 + minor1 * 1000000 + minor2 * 1000
        if minor3 != 0:
            total -= (100 - minor3)
        return total
    return 0


def version_compare(v1, v2):
    return version_to_number(v2) >= version_to_number(v1)


# Return true if 1st version is included in the current baseline.
# If no baseline is provided, use default.
def is_in_baseline(version, baseline=rebase_baseline()):
    if version:
      return version_compare(version, baseline)

    # If there is no version tag, it can not be included in any baseline.
    return False


# Return true if 1st version is included in the current baseline.
# If no baseline is provided, use default.
def is_in_target(version, target=rebase_target_tag()):
    if version:
      return version_compare(version, target)

    # If there is no version tag, it can not be included in any target.
    return False
