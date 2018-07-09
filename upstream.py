import sqlite3
import os
import subprocess
import re
# requires "pip install fuzzywuzzy"
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from config import rebasedb, upstreamdb, chromeos_path, upstream_path

rp = re.compile('(UPSTREAM: |FROMGIT: |FROMLIST: |BACKPORT: )(.*)')
rpf = re.compile('(FIXUP: |Fixup: )(.*)')

workdir = os.getcwd()

merge = sqlite3.connect(rebasedb)
upstream = sqlite3.connect(upstreamdb)

c = merge.cursor()
c2 = merge.cursor()

cu = upstream.cursor()

def get_patch(path, sha):
    os.chdir(path)
    patch = subprocess.check_output(['git', 'show', '--format="%b"', '-U1', sha])
    os.chdir(workdir)
    i = re.search("^diff", patch, flags=re.MULTILINE).group()
    if i:
	ind=patch.index(i)
	return patch[ind:]
    return

def patch_ratio(usha, lsha):
    lpatch = get_patch(upstream_path, usha)
    if lpatch:
        upatch = get_patch(chromeos_path, lsha)
	if upatch:
	    return (fuzz.ratio(upatch, lpatch), fuzz.token_set_ratio(upatch, lpatch))
    return (0, 0)

cu.execute("select description from commits")
alldescs=cu.fetchall()

c.execute("select sha, description, disposition from commits")
for (sha, desc, disposition) in c.fetchall():
    if disposition == "drop":
        continue
    m = rp.search(desc)
    mf = rpf.search(desc)
    if m:
        # print "Regex match for '%s'" % desc.replace("'", "''")
        ndesc = m.group(2)
        rdesc = m.group(2)
        # Try to match again to catch and remove multiple tags.
        m = rp.search(ndesc)
        while m:
          # print "  Recursive regex match for '%s'" % ndesc.replace("'", "''")
          ndesc = m.group(2)
          rdesc = m.group(2)
          m = rp.search(ndesc)
        ndesc=ndesc.replace("'", "''")
	# print "    Match subject '%s'" % ndesc
	cu.execute("select sha, description, in_baseline from commits where description='%s'" % ndesc)
	fsha = cu.fetchone()
	if fsha:
	    c2.execute("UPDATE commits SET dsha=('%s') where sha='%s'" % (fsha[0], sha))
	    in_baseline = fsha[2]
	    if mf:
                print "Regex match for %s '%s'" % (sha, desc.replace("'", "''"))
	        print "    Match subject '%s'" % ndesc
	        print "    FIXUP patch"
	        print "    Found matching upstream commit %s ('%s'), drop" % (fsha[0], fsha[1].replace("'", "''"))
		c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
		c2.execute("UPDATE commits SET reason=('upstream') where sha='%s'" % sha)
	        c2.execute("UPDATE commits SET sscore=100 where sha='%s'" % sha)
		continue
	    # print "    Upstream subject for %s matches %s" % (fsha[1], sha)
	    # print "    Local description: %s" % desc
	    # print "    Upstream description: %s" % ndesc
	    # print "    In v4.9: %d" % fsha[2]
	    if in_baseline == 1:
		c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
	    else:
		c2.execute("UPDATE commits SET disposition=('replace') where sha='%s'" % sha)
	    # This is a perfect match. Set sscore to 100.
	    c2.execute("UPDATE commits SET sscore=100 where sha='%s'" % sha)
	    (ratio, setratio) = patch_ratio(fsha[0], sha)
	    c2.execute("UPDATE commits SET pscore=%d where sha='%s'" %
							((ratio + setratio)/2, sha))
	    # Like many others, 160 is a magic number derived from experiments.
	    if ratio + setratio > 160:
	        c2.execute("UPDATE commits SET reason=('upstream') where sha='%s'" % sha)
	    else:
	        c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
	else:
            print "Regex match for '%s'" % desc.replace("'", "''")
	    print "    Match subject '%s'" % ndesc
	    print "    No upstream match for '%s' [marked as '%s'], trying fuzzy match" % (sha, disposition)
	    (mdesc, result) = process.extractOne(rdesc, alldescs, score_cutoff = 86)
	    # Looks like everything gets a match of 86.
	    if result <= 86:
	        print "    Basic subject match %d insufficient" % result
		# If the patch is tagged UPSTREAM:, but upstream does not have a matching
		# subject, something is odd. Need to revisit.
		if desc.startswith("UPSTREAM:"):
		    c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
		    c2.execute("UPDATE commits SET sscore=%d where sha='%s'" % (result, sha))
	        continue
	    smatch=fuzz.token_set_ratio(rdesc, mdesc)
	    print "    subject match results %d/%d" % (result, smatch)
	    c2.execute("UPDATE commits SET sscore=%d where sha='%s'" %
					((result + smatch)/2, sha))
	    cu.execute("select sha, description, in_baseline from commits where description='%s'" %
								mdesc[0].replace("'", "''"))
	    fsha = cu.fetchone()
	    if fsha:
		c2.execute("UPDATE commits SET dsha=('%s') where sha='%s'" % (fsha[0], sha))
	        in_baseline = fsha[2]
	        print "    Upstream candidate %s ('%s')" % (fsha[0], fsha[1].replace("'", "''"))
		if mf:
		    # We have:
		    #	sha is this patch
		    #	fsha[0] is the replacement candidate
		    c2.execute("select sha from commits where dsha is '%s'" % fsha[0])
		    dsha=c2.fetchone()
		    if dsha:
			print "    FIXUP: Found upstream patch as replacement target. dropping"
			c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
			c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
			c2.execute("UPDATE commits SET sscore=100 where sha='%s'" % sha)
		    else:
			print "    FIXUP: No replacement target. Revisit."
			c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
		    continue
		(ratio, setratio) = patch_ratio(fsha[0], sha)
		c2.execute("UPDATE commits SET pscore=%d where sha='%s'" %
							((ratio + setratio)/2, sha))
	        if (result <= 90 or smatch < 98) and smatch != 100 and (result <= 95 or smatch <= 95):
	            print "    Subject match %d/%d insufficient" % (result, smatch)
		    c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
	            continue
		c2.execute("select filename from files where sha is '%s'" % sha)
		lfilenames=c2.fetchall()
		cu.execute("select filename from files where sha is '%s'" % fsha[0])
		ufilenames=cu.fetchall()
		if lfilenames != ufilenames:
		    print "    File name mismatch, skipping"
		    c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
		    continue
	        print "    patch match results %d/%d" % (ratio, setratio)
		if (smatch < 100 and (ratio <= 90 or setratio <= 90)) or ratio <= 70:
	            print "    code match %d/%d insufficient" % (ratio, setratio)
		    print "    Mark sha '%s' for revisit" % sha
		    c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
		    continue
		# We have a match.
	        if in_baseline == 1:
		    print "    Drop sha '%s' (close match)" % sha
		    c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'" % sha)
		    c2.execute("UPDATE commits SET reason=('upstream') where sha='%s'" % sha)
	        else:
		    print "    Replace sha '%s' with '%s' (close match)" % (sha, fsha[0])
		    c2.execute("UPDATE commits SET disposition=('replace') where sha='%s'" % sha)
		    c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" % sha)
	    else:
		print "    NOTICE: missing upstream match for '%s'" % mdesc[0].replace("'", "''")

merge.commit()
merge.close()
upstream.close()
