import sqlite3
import os
import subprocess
from config import rebasedb, \
	stable_path, android_path, chromeos_path, \
	rebase_baseline, stable_baseline, rebase_target

stable_commits = rebase_baseline + '..' + stable_baseline

workdir = os.getcwd()

try:
    os.remove(rebasedb)
except:
    pass

conn = sqlite3.connect(rebasedb)
# conn.text_factory = str

c = conn.cursor()

# Create table
c.execute("CREATE TABLE commits (date integer, sha text, description text, \
				topic integer, disposition text, reason text, \
				sscore integer, pscore integer, dsha text)")
c.execute("CREATE UNIQUE INDEX commit_date ON commits (date)")
c.execute("CREATE INDEX commit_sha ON commits (sha)")

c.execute("CREATE TABLE files (sha text, filename text)")
c.execute("CREATE INDEX file_sha ON files (sha)")
c.execute("CREATE INDEX file_name ON files (filename)")

c.execute("CREATE TABLE stable (sha, origin)")
c.execute("CREATE UNIQUE INDEX stable_sha ON stable (sha)")

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

# Save (commit) the changes
conn.commit()

os.chdir(stable_path)
commits = subprocess.check_output(['git', 'log', '--oneline', '--reverse', stable_commits])
os.chdir(workdir)

# Create list of SHAs from stable release
for commit in commits.splitlines():
    if commit != "":
        elem = commit.split(" ")[:1]
        c.execute("INSERT INTO stable(sha, origin) VALUES (?, ?)", (elem[0], "stable", ))

conn.commit()

# Create list of SHAs from android 4.4.
# Skip if entry is already in database.
os.chdir(android_path)
commits = subprocess.check_output(['git', 'log', '--oneline', '--reverse', rebase_baseline + '..'])
os.chdir(workdir)

for commit in commits.splitlines():
    if commit != "":
	elem = commit.split(" ")[:1]
	sha=elem[0]
	c.execute("select sha from stable where sha is '%s'" % sha)
	found=c.fetchall()
	if found == []:
	    c.execute("INSERT INTO stable(sha, origin) VALUES (?, ?)", (sha, "android", ))

conn.commit()

# get complete list of commits from chromeos-4.4.
# Assume that the chromeos 4.4 branch exists and has been checked out.

os.chdir(chromeos_path)
commits = subprocess.check_output(['git', 'log', '--oneline', "--reverse", rebase_baseline + '..'])

prevdate=0
mprevdate=0
for commit in commits.splitlines():
    if commit != "":
        elem = commit.split(" ", 1)
	sha = elem[0]
        description = elem[1].rstrip('\n')
	description = description.decode('latin-1') if isinstance(description, str) else description
        sdate = subprocess.check_output(['git', 'show', '--format="%ct"', '-s', sha])
	sdate = sdate.rstrip('\n')
	sdate = sdate.strip('"')
	# Make sure date is unique and in ascending order.
	date = int(sdate)
	if date == prevdate:
	    date = mprevdate + 1
	else:
	    prevdate = date
	    date = date * 1000
	mprevdate = date
	# Initially assume we'll drop everything because it is not listed when
	# running "rebase -i".
        c.execute("INSERT INTO commits(date, sha, description, disposition, reason) VALUES (?, ?, ?, ?, ?)",
					(date, sha, description, "drop", "merge",))
	filenames = subprocess.check_output(['git', 'show', '--name-only', '--format=', sha])
        for fn in filenames.splitlines():
            if fn != "":
                c.execute("INSERT INTO files(sha, filename) VALUES (?, ?)", (sha,fn,))

conn.commit()

# "git cherry -v <target>" on branch rebase_baseline gives us a list
# of patches to apply.
patches = subprocess.check_output(['git', 'cherry', '-v', rebase_target])
for patch in patches.splitlines():
    elem = patch.split(" ", 2)
    # print "patch: " + patch
    # print "elem[0]: '%s' elem[1]: '%s' elem[2]: '%s'" % (elem[0], elem[1], elem[2])
    if elem[0] == "+":
	# patch not found upstream
	sha = elem[1][:12]
	# Try to find patch in stable branch. If it is there, drop it after all.
	# If not, we may need to apply it.
        c.execute("select sha, origin from stable where sha is '%s'" % sha)
	found=c.fetchone()
        if found:
	    c.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
	    c.execute("UPDATE commits SET reason=('%s') where sha='%s'" % (found[1], sha))
        else:
	    c.execute("UPDATE commits SET disposition=('pick') where sha='%s'" % sha)
	    c.execute("UPDATE commits SET reason=('') where sha='%s'" % sha)

os.chdir(workdir)
conn.commit()
conn.close()
