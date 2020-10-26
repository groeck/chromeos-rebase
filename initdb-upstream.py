import os
import re
import sqlite3
import subprocess
from common import upstream_path
from common import rebase_baseline, workdir, upstreamdb, createdb, rebase_target_tag
from common import get_integrated_tag, DEVNULL


def mktables(c):
  ''' Create tables '''
  c.execute("CREATE TABLE commits (committed timestamp, sha text, patchid text, subject text, integrated text)")
  c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")
  c.execute("CREATE INDEX patchid ON commits (patchid)")

  c.execute("CREATE TABLE files (sha text, filename text)")
  c.execute("CREATE INDEX file_sha ON files (sha)")
  c.execute("CREATE INDEX file_name ON files (filename)")

  c.execute("CREATE TABLE tags (tag text, timestamp timestamp)")
  c.execute("CREATE UNIQUE INDEX tag ON tags (tag)")


def update_integrated_table(c, integrated):

  cmd = ['git', '-C', upstream_path, 'log', '-1', '--format=%ct', integrated]
  output = subprocess.check_output(cmd, stderr=DEVNULL)
  timestamp = int(output.splitlines()[0])

  try:
    c.execute("INSERT INTO tags(tag, timestamp) VALUES (?, ?)", (integrated, timestamp))
  except:
    # Assume this is a duplicate and ignore errors
    pass


def handle(c, range):
  commits = subprocess.check_output(['git', 'log', '--abbrev=12', '--format=%ct %h %s', '--reverse', range])
  last = None
  for commit in commits.splitlines():
    if commit != "":
      elem = commit.split(" ", 2)
      timestamp = elem[0]
      sha = elem[1]
      last = sha

      # Check if commit is a merge. If so, nothing else to do.
      l = subprocess.check_output(['git', 'rev-list', '--parents', '-n', '1', sha],
                                  stderr=DEVNULL)
      if len(l.split(' ')) > 2:
	continue

      subject = elem[2].rstrip('\n')
      subject = subject.decode('latin-1') if isinstance(subject, str) else subject
      integrated = get_integrated_tag(sha)

      if integrated:
          update_integrated_table(c, integrated)

      ps = subprocess.Popen(['git', 'show', sha], stdout=subprocess.PIPE)
      spid = subprocess.check_output(['git', 'patch-id'], stdin=ps.stdout)
      patchid = spid.split(" ", 1)[0]

      print("%s %s %s %s" % (timestamp, sha, patchid, integrated))

      try:
        c.execute("INSERT INTO commits(committed, sha, patchid, subject, integrated) VALUES (?, ?, ?, ?, ?)",
                  (timestamp, sha, patchid, subject, integrated))
        filenames = subprocess.check_output(['git', 'show', '--name-only', '--format=', sha])
        for fn in filenames.splitlines():
          if fn != "":
            c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha, fn))
      except error as e:
        # The commit may already be in the database. If so, just keep going.
	print(e)
        pass

  if last:
    c.execute("UPDATE tip set sha='%s' where ref=1" % last)


def update_baseline():

  conn = sqlite3.connect(upstreamdb)
  c = conn.cursor()
  c.execute('select sha from commits where integrated is NULL')
  for sha, in c.fetchall():
    integrated = get_integrated_tag(sha)
    if integrated:
      print("Updating sha %s: integrated=%s" % (sha, integrated))
      update_integrated_table(c, integrated)
      cmd='UPDATE commits SET integrated="%s" where sha="%s"' % (integrated, sha)
      c.execute(cmd)
  conn.commit()
  conn.close()


# Should not be needed anymore. Keep around just in case.
def init_tags(c):
  c.execute('SELECT integrated FROM commits WHERE integrated IS NOT Null')
  all_integrated = [ ]
  for integrated, in c.fetchall():
    if integrated not in all_integrated:
      update_integrated_table(c, integrated)
      all_integrated += [integrated]


def update_patchids(c):
  c.execute('SELECT sha FROM commits WHERE patchid is Null')
  for sha, in c.fetchall():
    ps = subprocess.Popen(['git', '-C', upstream_path, 'show', sha],
                          stdout=subprocess.PIPE)
    spid = subprocess.check_output(['git', 'patch-id'], stdin=ps.stdout)
    patchid = spid.split(" ", 1)[0]
    print("sha %s patch-id %s" % (sha, patchid))
    c.execute("UPDATE commits SET patchid=('%s') where sha='%s'" % (patchid, sha))


def update_upstreamdb():
  start = rebase_baseline()

  try:
    # see if we previously handled anything. If yes, use it.
    # Otherwise re-create database.
    conn = sqlite3.connect(upstreamdb)
    c = conn.cursor()
    c.execute("select sha from tip")
    sha, = c.fetchone()
    conn.close()
    print("Last handled sha: %s" % sha)
    if sha:
      start = sha
      # In this case, integration status may have changed.
      # Update database accordingly.
      update_baseline()
    else:
      fail
  except:
    createdb(upstreamdb, mktables)

  os.chdir(upstream_path)

  print("Starting with SHA %s" % start)

  range = start + '..'

  conn = sqlite3.connect(upstreamdb)
  c = conn.cursor()

  # init_tags(c)
  # conn.commit()

  update_patchids(c)
  conn.commit()

  handle(c, range)

  conn.commit()
  conn.close()

  os.chdir(workdir)

if __name__ == "__main__":
  update_upstreamdb()
