# -*- coding: utf-8 -*-"
from __future__ import print_function

from collections import defaultdict
# requires "pip install fuzzywuzzy"
import operator
import os
import re
import subprocess

from config import chromeos_path
from config import rebasedb
from config import upstream_path
from config import upstreamdb
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import sqlite3

# List of all subjects, split into dictionary indexed by each word
# in the subject.
_alldescs = defaultdict(list)


def get_patch(path, psha):
  workdir = os.getcwd()
  os.chdir(path)
  patch = subprocess.check_output(["git", "show", "--format='%b'", "-U1", psha])
  os.chdir(workdir)
  i = re.search("^diff", patch, flags=re.MULTILINE).group()
  if i:
    ind = patch.index(i)
    return patch[ind:]
  return


def patch_ratio(usha, lsha):
  lpatch = get_patch(upstream_path, usha)
  if lpatch:
    upatch = get_patch(chromeos_path, lsha)
    if upatch:
      return (fuzz.ratio(upatch, lpatch), fuzz.token_set_ratio(upatch, lpatch))
  return (0, 0)


def best_match(s):
  """Find best match for subject in _alldescs.

  Split provided subject into words. Search for subject in each of the
  word lists.

  Args:
    s: The subject to match.

  Returns:
    Best subject match as list (subject, score). If multiple subjects match
    with the same score, return first encountered match with this score.
  """

  matches = []
  s = re.sub("[^a-zA-Z0-9_ ]+", "", s)
  for word in s.split():
    match = process.extractOne(s, _alldescs[word],
                               scorer=fuzz.token_sort_ratio, score_cutoff=65)
    if match:
      matches.append(match)
  if not matches:
    return ("", 0)
  best = max(matches, key=operator.itemgetter(1))
  return (best[0], best[1])


def getallsubjects():
  """Split descriptions into a dictionary of of word-hashed lists.

  By searching the resulting lists, we can speed up processing
  significantly.

  Returns:
    _alldescs[] is populated.
  """

  upstream = sqlite3.connect(upstreamdb)
  cu = upstream.cursor()
  cu.execute("select description from commits")
  for desc in cu.fetchall():
    subject = re.sub("[^a-zA-Z0-9_ ]+", "", desc[0])
    words = subject.split()
    for word in words:
      _alldescs[word].append(desc[0])
  upstream.close()

def doit():
  """Do the actual work.

  Read all commits from database, compare against upstream commits,
  and mark accordingly.
  """

  rp = re.compile("(CHROMIUM: *|CHROMEOS: *|UPSTREAM: *|FROMGIT: *|FROMLIST: *|BACKPORT: *)+(.*)")
  rpf = re.compile("(FIXUP: *|Fixup: *)(.*)")

  merge = sqlite3.connect(rebasedb)
  c = merge.cursor()
  c2 = merge.cursor()
  upstream = sqlite3.connect(upstreamdb)
  cu = upstream.cursor()

  c.execute("select sha, description, disposition from commits")
  for (sha, desc, disposition) in c.fetchall():
    if disposition == "drop":
      continue
    m = rp.search(desc)
    mf = rpf.search(desc)
    if m:
      # print("Regex match for '%s'" % desc.replace("'", "''"))
      ndesc = m.group(2).replace("'", "''")
      rdesc = m.group(2)
      # print("    Match subject '%s'" % ndesc)
      cu.execute("select sha, description, in_baseline from commits "
                 "where description='%s'"
                 % ndesc)
      fsha = cu.fetchone()
      if fsha:
        c2.execute("UPDATE commits SET dsha=('%s') where sha='%s'"
                   % (fsha[0], sha))
        in_baseline = fsha[2]
        if mf:
          print("Regex match for %s '%s'" % (sha, desc.replace("'", "''")))
          print("    Match subject '%s'" % ndesc)
          print("    FIXUP patch")
          print("    Found matching upstream commit %s ('%s'), drop" %
                (fsha[0], fsha[1].replace("'", "''")))
          c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'"
                     % sha)
          c2.execute("UPDATE commits SET reason=('upstream') where sha='%s'"
                     % sha)
          c2.execute("UPDATE commits SET sscore=100 where sha='%s'" % sha)
          continue
        # print("    Upstream subject for %s matches %s" % (fsha[1], sha))
        # print("    Local description: %s" % desc)
        # print("    Upstream description: %s" % ndesc)
        # print("    In v4.9: %d" % fsha[2])
        if in_baseline == 1:
          c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'"
                     % sha)
        else:
          c2.execute("UPDATE commits SET disposition=('replace') where sha='%s'"
                     % sha)
        # This is a perfect match. Set sscore to 100.
        c2.execute("UPDATE commits SET sscore=100 where sha='%s'" % sha)
        (ratio, setratio) = patch_ratio(fsha[0], sha)
        c2.execute("UPDATE commits SET pscore=%d where sha='%s'" %
                   ((ratio + setratio)/2, sha))
        # Like many others, 160 is a magic number derived from experiments.
        if ratio + setratio > 160:
          c2.execute("UPDATE commits SET reason=('upstream') where sha='%s'" %
                     sha)
        else:
          c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'" %
                     sha)
      else:
        print("Regex match for '%s'" % desc.replace("'", "''"))
        print("    Match subject '%s'" % ndesc)
        print("    No upstream match for '%s' [marked %s], trying fuzzy match"
              % (sha, disposition))
        (mdesc, result) = best_match(rdesc)
        if result == 0:
          print("    No close match")
          continue
        if result <= 75:
          print("    Best candidate: %s" % mdesc)
          print("    Basic subject match %d insufficient" % result)
          # If the patch is tagged UPSTREAM:, but upstream does not have
          # a matching subject, something is odd. Need to revisit.
          if desc.startswith("UPSTREAM:"):
            c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'"
                       % sha)
            c2.execute("UPDATE commits SET sscore=%d where sha='%s'"
                       % (result, sha))
          continue
	# Use default ratio (not fuzz.token_sort_ratio) for further matching.
        result = fuzz.ratio(rdesc, mdesc)
        smatch = fuzz.token_set_ratio(rdesc, mdesc)
        print("    subject match results %d/%d" % (result, smatch))
        c2.execute("UPDATE commits SET sscore=%d where sha='%s'" %
                   ((result + smatch)/2, sha))
        cu.execute("select sha, description, in_baseline from commits "
                   "where description='%s'" % mdesc.replace("'", "''"))
        fsha = cu.fetchone()
        if fsha:
          c2.execute("UPDATE commits SET dsha=('%s') where sha='%s'"
                     % (fsha[0], sha))
          in_baseline = fsha[2]
          print("    Upstream candidate %s ('%s')" %
                (fsha[0], fsha[1].replace("'", "''")))
          if mf:
            # We have:
            #        sha is this patch
            #        fsha[0] is the replacement candidate
            c2.execute("select sha from commits where dsha is '%s'" % fsha[0])
            dsha = c2.fetchone()
            if dsha:
              print("    FIXUP: Found upstream patch as replacement. dropping")
              c2.execute("UPDATE commits SET disposition=('drop') "
                         "where sha='%s'" % sha)
              c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'"
                         % sha)
              c2.execute("UPDATE commits SET sscore=100 where sha='%s'" % sha)
            else:
              print("    FIXUP: No replacement target. Revisit.")
              c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'"
                         % sha)
            continue
          (ratio, setratio) = patch_ratio(fsha[0], sha)
          c2.execute("UPDATE commits SET pscore=%d where sha='%s'" %
                     ((ratio + setratio)/2, sha))
          if ((result <= 90 or smatch < 98) and smatch != 100 and
              (result <= 95 or smatch <= 95)):
            print("    Subject match %d/%d insufficient" % (result, smatch))
            c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'"
                       % sha)
            continue
          c2.execute("select filename from files where sha is '%s'" % sha)
          lfilenames = c2.fetchall()
          cu.execute("select filename from files where sha is '%s'" % fsha[0])
          ufilenames = cu.fetchall()
          if lfilenames != ufilenames:
            print("    File name mismatch, skipping")
            c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'"
                       % sha)
            continue
          print("    patch match results %d/%d" % (ratio, setratio))
          if (smatch < 100 and (ratio <= 90 or setratio <= 90)) or ratio <= 70:
            print("    code match %d/%d insufficient" % (ratio, setratio))
            print("    Mark sha '%s' for revisit" % sha)
            c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'"
                       % sha)
            continue
          # We have a match.
          if in_baseline == 1:
            print("    Drop sha '%s' (close match)" % sha)
            c2.execute("UPDATE commits SET disposition=('drop') where sha='%s'"
                       % sha)
            c2.execute("UPDATE commits SET reason=('upstream') where sha='%s'"
                       % sha)
          else:
            print("    Replace sha '%s' with '%s' (close match)" %
                  (sha, fsha[0]))
            c2.execute("UPDATE commits SET disposition=('replace') "
                       "where sha='%s'" % sha)
            c2.execute("UPDATE commits SET reason=('revisit') where sha='%s'"
                       % sha)
        else:
          print("    NOTICE: missing upstream match for '%s'" %
                mdesc.replace("'", "''"))

  merge.commit()
  merge.close()
  upstream.close()

getallsubjects()
doit()
