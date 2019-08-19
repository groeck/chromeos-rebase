import os
import re
import sqlite3
import subprocess
from config import upstreamdb, upstream_path, rebase_baseline, rebase_target

upstream_drop = rebase_baseline + '..' + rebase_target
upstream_pick = rebase_target + '..'

workdir = os.getcwd()

try:
    os.remove(upstreamdb)
except:
    pass

rf = re.compile('^\s*Fixes: ([a-zA-Z0-9]+).*')
rdesc = re.compile('.* \("([^"]+)"\).*')

conn = sqlite3.connect(upstreamdb)

c = conn.cursor()
c2 = conn.cursor()

# Create tables
c.execute("CREATE TABLE commits (sha text, description text, in_baseline integer)")
c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")

c.execute("CREATE TABLE files (sha text, filename text)")
c.execute("CREATE INDEX file_sha ON files (sha)")
c.execute("CREATE INDEX file_name ON files (filename)")

c.execute("CREATE TABLE fixes (sha text, fsha text)")
c.execute("CREATE INDEX sha ON fixes (sha)")

conn.commit()

os.chdir(upstream_path)

def handle(range, baseline):
    commits = subprocess.check_output(['git', 'log', '--abbrev=12', '--oneline', '--no-merges', '--reverse', range])
    for commit in commits.splitlines():
      if commit != "":
        elem = commit.split(" ", 1)
        sha = elem[0]
        description = elem[1].rstrip('\n')
        description = description.decode('latin-1') if isinstance(description, str) else description
        c.execute("INSERT INTO commits(sha, description, in_baseline) VALUES (?, ?, ?)",
                  (sha, description, baseline,))
        filenames = subprocess.check_output(['git', 'show', '--name-only', '--format=', sha])
        for fn in filenames.splitlines():
          if fn != "":
            c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha, fn))
        # Now check if this patch fixes a previous patch.
        description = subprocess.check_output(['git', 'show', '-s', '--pretty=format:%b', sha])
        for d in description.splitlines():
          m = rf.search(d)
          fsha=None
          if m and m.group(1):
            try:
              # Normalize fsha to 12 characters.
              cmd = 'git show -s --pretty=format:%%H %s 2>/dev/null' % m.group(1)
              fsha = subprocess.check_output(cmd, shell=True)
            except:
              print "Commit '%s' for SHA '%s': Not found" % (m.group(0), sha)
              m=rdesc.search(d)
              if m:
                desc=m.group(1)
                desc = desc.replace("'", "''")
                c2.execute("select sha from commits where description is '%s'" % desc)
                fsha = c2.fetchone()
                if fsha:
                  fsha=fsha[0]
                  print "  Real SHA is '%s'" % fsha
              # The Fixes: tag may be wrong. The sha may not be in the
              # upstream kernel, or the format may be completely wrong and
              # m.group(1) may not be a sha in the first place.
              # In that case, do nothing.
              pass
          if fsha:
            print "Commit %s has been fixed by %s" % (fsha[0:12], sha)
            # Insert in reverse order: sha is fixed by fsha
            c.execute("INSERT into fixes (sha, fsha) VALUES (?, ?)", (fsha[0:12], sha))

    conn.commit()

handle(upstream_drop, 1)
handle(upstream_pick, 0)

conn.close()
