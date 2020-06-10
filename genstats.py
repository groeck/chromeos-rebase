#!/usr/bin/env python2
# -*- coding: utf-8 -*-"
#
# Use information in rebase database to create rebase spreadsheet
# Required python modules:
# google-api-python-client google-auth-httplib2 google-auth-oauthlib
#
# The Google Sheets API needs to be enabled to run this script.
# Also, you'll need to generate access credentials and store those
# in credentials.json.

from __future__ import print_function

import sqlite3
import os
import re
import subprocess
import datetime
import time
import pickle

from googleapiclient import discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from config import rebasedb, topiclist_condensed
from common import upstreamdb, rebase_baseline, rebase_target_version

stats_filename = "rebase-stats.id"

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

rp = re.compile("(CHROMIUM: *|CHROMEOS: *|UPSTREAM: *|FROMGIT: *|FROMLIST: *|BACKPORT: *)+(.*)")

red = { 'red': 1, 'green': 0.4, 'blue': 0 }
yellow = { 'red': 1, 'green': 1, 'blue': 0 }
orange = { 'red': 1, 'green': 0.6, 'blue': 0 }
green = { 'red': 0, 'green': 0.9, 'blue': 0 }
blue = { 'red': 0.3, 'green': 0.6, 'blue': 1 }
white = { 'red': 1, 'green': 1, 'blue': 1 }

lastrow = 0

version = rebase_target_version()

def NOW():
  return int(time.time())


def get_other_topic_id(c):
    """ Calculate other_topic_id """

    other_topic_id = 0

    c.execute("select topic, name from topics order by name")
    for topic, name in c.fetchall():
        if name is 'other':
            return topic
        if topic >= other_topic_id:
            other_topic_id = topic + 1

    return other_topic_id


def get_condensed_topic_name(topic_name):

    for [condensed_name, topic_names] in topiclist_condensed:
        for elem in topic_names:
            if topic_name == elem:
                return condensed_name
    return topic_name


def get_condensed_topic(c, topic_name):
    for [condensed_name, topic_names] in topiclist_condensed:
        for elem in topic_names:
            if topic_name == elem:
                c.execute("select topic from topics where name is '%s'" % topic_names[0])
                topic = c.fetchone()
                if topic:
                    return topic[0]
    c.execute("select topic from topics where name is '%s'" % topic_name)
    topic = c.fetchone()
    if topic:
        return topic[0]
    # oops
    print("No topic found for %s" % topic_name)
    return 0


def get_topic_name(c, topic):

    c.execute("select name from topics where topic is '%s'" % topic)
    topic = c.fetchone()
    if topic:
        return topic[0]

    return None

def get_topics(c):
    topics = {}
    other_topic_id = None

    c.execute("SELECT topic, name FROM topics ORDER BY name")
    for topic, name in c.fetchall():
        if name:
            condensed_name = get_condensed_topic_name(name)
            condensed_topic = get_condensed_topic(c, name)
            topics[topic] = condensed_name
            if condensed_name is 'other':
                other_topic_id = condensed_topic

    if not other_topic_id:
        topics[get_other_topic_id(c)] = 'other'

    return topics


def get_tags(cu=None):
    """Get dictionary with list of tags. Index is tag, content is tag timestamp"""

    uconn = None
    if not cu:
        uconn = sqlite3.connect(upstreamdb)
        cu = uconn.cursor()

    tag_list = {}
    largest_ts = 0

    cu.execute("SELECT tag, timestamp FROM tags ORDER BY timestamp")
    for (tag, timestamp) in cu.fetchall():
        tag_list[tag] = timestamp
        if timestamp > largest_ts:
            largest_ts = timestamp

    tag_list[u'ToT'] = largest_ts + 1

    if uconn:
        uconn.close()

    return tag_list


def do_topic_stats_count(topic_stats, tags, topic, committed_ts, integrated_ts):
    """Count commit in topic stats if appropriate"""

    for tag in tags:
        tag_ts = tags[tag]
        if committed_ts < tag_ts and tag_ts < integrated_ts:
            topic_stats[topic][tag] += 1


def get_topic_stats(c):
    """ Return dict with commit statistics"""

    uconn = sqlite3.connect(upstreamdb)
    cu = uconn.cursor()

    other_topic_id = get_other_topic_id(c)
    tags = get_tags(cu)
    topics = get_topics(c)

    topic_stats = {}
    for topic in list(set(topics.values())):
        topic_stats[topic] = {}
        for tag in tags:
            topic_stats[topic][tag] = 0

    c.execute("SELECT sha, usha, dsha, committed, topic, disposition from commits")
    for (sha, usha, dsha, committed, topic, disposition,) in c.fetchall():
        if topic in topics:
            topic_name = topics[topic]
        else:
            topic_name = 'other'
        if disposition != 'drop':
            do_topic_stats_count(topic_stats, tags, topic_name, committed, NOW())
            continue
        if not usha:
            usha = dsha
        if usha:
            cu.execute("SELECT integrated from commits where sha is '%s'" % usha)
            integrated = cu.fetchone()
            if integrated:
                integrated = integrated[0] if integrated[0] else None
            if integrated:
                # print("Counting sha %s topic %d disposition %s from %s to %s" % (sha, topic, disposition, committed, integrated))
                do_topic_stats_count(topic_stats, tags, topic_name, committed, tags[integrated])
            else: # Not yet integrated
                if disposition != 'drop':
                    # print("Counting sha %s topic %d disposition %s from %s (not integrated)" % (sha, topic, disposition, committed))
                    do_topic_stats_count(topic_stats, tags, topic_name, committed, NOW())
                else:
                    # print("Counting sha %s topic %d disposition %s from %s to ToT" % (sha, topic, disposition, committed))
                    do_topic_stats_count(topic_stats, tags, topic_name, committed, tags['ToT'])

    uconn.close()

    return topic_stats


def getsheet():
    """ Get and return reference to spreadsheet """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = discovery.build('sheets', 'v4', credentials=creds)
    # service = discovery.build('sheets', 'v4', developerKey=API_KEY)
    return service.spreadsheets()


def doit(sheet, id, requests):
    ''' Execute a request '''
    body = {
        'requests': requests
    }

    request = sheet.batchUpdate(spreadsheetId=id, body=body)
    response = request.execute()
    return response


def hide_sheet(sheet, id, sheetid, hide):
    ''' Move 'Data' sheet to end of spreadsheet. '''
    request = [ ]

    request.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheetid,
                'hidden': hide,
            },
            'fields': 'hidden'
        }
    })

    doit(sheet, id, request)


def create_spreadsheet(sheet, title):
    """ Create a spreadsheet and return reference to it """
    spreadsheet = {
        'properties': {
            'title': title
        }
    }

    request = sheet.create(body=spreadsheet, fields='spreadsheetId')
    response = request.execute()

    return response.get('spreadsheetId')


def delete_sheets(sheet, id, sheets):
    ''' Delete all sheets except sheet 0. In sheet 0, delete all values. '''
    # Unhide 'Data' sheet. If it is hidden we can't remove the other sheets.
    hide_sheet(sheet, id, 0, False)
    request = [ ]
    for s in sheets:
      sheetId = s['properties']['sheetId']
      if sheetId != 0:
        request.append({
          "deleteSheet": {
            "sheetId": sheetId
          }
        })
      else:
        request.append({
          "updateCells": {
            "range": {
              "sheetId": sheetId
            },
            "fields": "userEnteredValue"
          }
        })

    # We are letting this fail if there was nothing to clean. This will
    # hopefully result in re-creating the spreadsheet.
    doit(sheet, id, request)


def init_spreadsheet(sheet):
    try:
        with open(stats_filename, 'r') as file:
            id = file.read().strip('\n')
        request = sheet.get(spreadsheetId=id, ranges = [ ], includeGridData=False)
        response = request.execute()
        sheets = response.get('sheets')
        delete_sheets(sheet, id, sheets)
    except:
        id = create_spreadsheet(sheet, 'Backlog Status for chromeos-%s' % rebase_baseline().strip('v'))
        with open(stats_filename, 'w') as file:
            file.write(id)

    return id


def resize_sheet(requests, id, start, end):
    requests.append({
      'autoResizeDimensions': {
        'dimensions': {
          'sheetId': id,
          'dimension': 'COLUMNS',
          'startIndex': start,
          'endIndex': end
        }
      }
    })


def add_topics_summary_row(requests, conn, rowindex, topic, name):
    c = conn.cursor()
    c2 = conn.cursor()

    age = 0
    now = NOW()
    if topic:
        search="select topic, authored, subject, disposition from commits where topic=%d" % topic
    else:
        search="select topic, authored, subject, disposition from commits where topic != 0"
    c.execute(search)
    rows = 0
    effrows = 0
    upstream = 0
    fromlist =  0
    fromgit = 0
    chromium = 0
    backport = 0
    other = 0
    for (t, a, subject, d) in c.fetchall():
        if topic == 0:
            c2.execute("select topic from topics where topic is %d" % t)
            # If the retrieved topic is in the named topic list, we are only
            # interested if we are not looking for 'other' topics.
            if c2.fetchall():
                continue
        rows += 1
        if d == 'pick':
            effrows += 1
            age += (now - a)
            m = rp.search(subject)
            if m:
                what = m.group(1).replace(" ", "")
                if what == "BACKPORT:":
                    m = rp.search(m.group(2))
                    if m:
                        what = m.group(1).replace(" ", "")
                if what == "CHROMIUM:" or what == "CHROMEOS:":
                    chromium += 1
                elif what == "UPSTREAM:":
                    upstream += 1
                elif what == "FROMLIST:":
                    fromlist += 1
                elif what == "FROMGIT:":
                    fromgit += 1
                elif what == "BACKPORT:":
                    backport += 1
                else:
                    other += 1
            else:
                other += 1

    # Only add summary entry if there are active commits associated with this topic.
    # Since the summary entry is used to generate statistics, do not add rows
    # where all commits have been pushed upstream or have been reverted.
    if effrows:
        age /= effrows
        age /= (3600 * 24)        # Display age in days
        requests.append({
            'pasteData': {
                'data': '%s;%d;%d;%d;%d;%d;%d;%d;%d;%d' % (name, upstream, backport, fromgit, fromlist, chromium, other, effrows, rows, age),
                'type': 'PASTE_NORMAL',
                'delimiter': ';',
                'coordinate': {
                    'sheetId': 0,
                    'rowIndex': rowindex
                }
            }
        })
    return effrows


def add_topics_summary(requests):
    global lastrow

    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()

    # Handle 'chromeos' first and separately so we can exclude it from the
    # backlog chart later.
    c.execute("select topic from topics where name is 'chromeos'")
    topic = c.fetchone()
    if topic:
        add_topics_summary_row(requests, conn, 1, topic[0], 'chromeos')

    c.execute("select topic, name from topics order by name")
    rowindex = 2
    for (topic, name) in c.fetchall():
        if name != 'chromeos':
            added = add_topics_summary_row(requests, conn, rowindex,
                                           topic, name)
            if added:
                rowindex += 1

    # Finally, do the same for 'other' topics, identified as topic==0.
    added = add_topics_summary_row(requests, conn, rowindex, 0, "other")

    lastrow = rowindex
    conn.close()


def add_sheet_header(requests, id, fields):
    """
    Add provided header line to specified sheet.
    Make it bold.

    Args:
        requests: Reference to list of requests to send to API.
        id: Sheet Id
        fields: string with comma-separated list of fields
    """
    # Generate header row
    requests.append({
        'pasteData': {
                    'data': fields,
                    'type': 'PASTE_NORMAL',
                    'delimiter': ',',
                    'coordinate': {
                        'sheetId': id,
                        'rowIndex': 0
                    }
                }
    })

    # Convert header row to bold and centered
    requests.append({
        "repeatCell": {
        "range": {
          "sheetId": id,
          "startRowIndex": 0,
          "endRowIndex": 1
        },
        "cell": {
          "userEnteredFormat": {
            "horizontalAlignment" : "CENTER",
            "textFormat": {
              "bold": True
            }
          }
        },
        "fields": "userEnteredFormat(textFormat,horizontalAlignment)"
        }
    })


def create_summary(sheet, id):
    requests = [ ]

    requests.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': 0,
                'title': 'Data',
            },
            'fields': 'title'
        }
    })

    add_sheet_header(requests, 0, 'Topic, Upstream, Backport, Fromgit, Fromlist, Chromium, Untagged/Other, Net, Total, Average Age (days)')

    # Now add all topics
    add_topics_summary(requests)

    # As final step, resize it
    resize_sheet(requests, 0, 0, 10)

    # and execute
    doit(sheet, id, requests)


def update_one_cell(request, sheetId, row, column, data):
    '''Update data in a a single cell'''

    print("update_one_cell(id=%d row=%d column=%d data=%s type=%s" % (sheetId, row, column, data, type(data)))

    if type(data) is int:
        fieldtype = 'numberValue'
    else:
        fieldtype = 'stringValue'

    request.append({
        'updateCells': {
            'rows': {
                'values': [{
                    'userEnteredValue': { fieldtype: '%s' % data }
                }]
            },
            'fields': 'userEnteredValue(stringValue)',
            'range': {
                'sheetId': sheetId,
                'startRowIndex': row,
                'startColumnIndex': column
                # 'endRowIndex': 1
                # 'endColumnIndexIndex': column + 1
            },
        }
    })



def add_topic_stats_column(request, sheetId, column, tag, data):
    """Add one column of topic statistics to request"""

    row = 0
    update_one_cell(request, sheetId, row, column, tag)

    data.pop(0) # First entry is topic 0, skip
    for f in data:
        row += 1
        update_one_cell(request, sheetId, row, column, f)


def create_topic_stats(sheet, id):
    """ Create tab with topic statistics. We'll use it later to create a chart."""

    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()

    topic_stats = get_topic_stats(c)
    tags = get_tags()
    sorted_tags = sorted(tags, key=tags.get)
    topics = get_topics(c)
    topic_list = list(set(topics.values()))

    request = []

    request.append({
        'addSheet': {
            'properties': {
                # 'sheetId': 1,
                'title': 'Topic Statistics Data',
            },
        }
    })

    response = doit(sheet, id, request)
    reply = response.get('replies')
    sheetId = reply[0]['addSheet']['properties']['sheetId']

    request = []

    # One column per topic
    header = ''
    columns = 1
    for topic in topic_list:
        header += ', %s' % topic
        columns += 1

    add_sheet_header(request, sheetId, header)

    rowindex = 1
    for tag in sorted_tags:
        # topic = topics[topic_num]
        # rowdata = topic
        rowdata = tag
        for topic in topic_list:
            rowdata += ';%d' % topic_stats[topic][tag]
        request.append({
            'pasteData': {
                'data': rowdata,
                'type': 'PASTE_NORMAL',
                'delimiter': ';',
                'coordinate': {
                    'sheetId': sheetId,
                    'rowIndex': rowindex
                }
            }
        })
        rowindex = rowindex + 1

    # As final step, resize sheet
    # [not really necessary; drop if confusing]
    resize_sheet(request, sheetId, 0, columns)

    # and execute
    doit(sheet, id, request)

    conn.close()

    return sheetId, rowindex, columns

def move_sheet(sheet, id, sheetid, to):
    ''' Move 'Data' sheet to end of spreadsheet. '''
    request = [ ]

    request.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheetid,
                'index': to,
            },
            'fields': 'index'
        }
    })

    doit(sheet, id, request)


def sourceRange(sheetId, rows, column):
    return {
      "sourceRange": {
        "sources": [
            {
                "sheetId": sheetId,
                "startRowIndex": 0,
                "endRowIndex": rows,
                "startColumnIndex": column,
                "endColumnIndex": column + 1
            }
        ]
      }
    }


def scope(name, sheetId, rows, column):
    return { name: sourceRange(sheetId, rows, column) }


def sscope(name, sheetId, rows, start, end):
    s = [ scope(name, sheetId, rows, start) ]
    while start < end:
        start += 1
        s += [ scope(name, sheetId, rows, start) ]
    return s


def add_backlog_chart(sheet, id):
    global lastrow

    request = [ ]

    # chart start with summary row 2. Row 1 is assumed to be 'chromeos'
    # which is not counted as backlog.
    request.append({
      'addChart': {
        "chart": {
          "chartId": 1,
          "spec": {
            "title": "Upstream Backlog (updated %s)" % datetime.datetime.now().strftime("%x"),
            "basicChart": {
              "chartType": "COLUMN",
              "stackedType": "STACKED",
              # "legendPosition": "BOTTOM_LEGEND",
              "axis": [
                {
                  "position": "BOTTOM_AXIS",
                  "title": "Topic"
                },
                {
                  "position": "LEFT_AXIS",
                  "title": "Backlog"
                }
              ],
              "domains": [ scope("domain", 0, lastrow + 1, 0) ],
              "series": sscope("series", 0, lastrow + 1, 1, 6),
            }
          },
          "position": {
            "newSheet": True,
          }
        }
      }
    })

    response = doit(sheet, id, request)

    # Extract sheet Id from response
    reply = response.get('replies')
    sheetId = reply[0]['addChart']['chart']['position']['sheetId']

    request = [ ]
    request.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheetId,
                'title': 'Backlog Count',
            },
            'fields': "title",
        }
    })
    doit(sheet, id, request)


def add_age_chart(sheet, id):
    global lastrow

    request = [ ]

    request.append({
      'addChart': {
        "chart": {
          "chartId": 2,
          "spec": {
            "title": "Upstream Backlog Age (updated %s)" % datetime.datetime.now().strftime("%x"),
            "basicChart": {
              "chartType": "COLUMN",
              # "legendPosition": "BOTTOM_LEGEND",
              "axis": [
                {
                  "position": "BOTTOM_AXIS",
                  "title": "Topic"
                },
                {
                  "position": "LEFT_AXIS",
                  "title": "Average Age (days)"
                }
              ],
              "domains": [ scope("domain", 0, lastrow + 1, 0) ],
              "series": [ scope("series", 0, lastrow + 1, 9) ]
            }
          },
          "position": {
            "newSheet": True,
          }
        }
      }
    })

    response = doit(sheet, id, request)

    # Extract sheet Id from response
    reply = response.get('replies')
    sheetId = reply[0]['addChart']['chart']['position']['sheetId']

    request = [ ]
    request.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheetId,
                'title': 'Backlog Age',
            },
            'fields': "title",
        }
    })
    doit(sheet, id, request)


def add_stats_chart(sheet, id, sheetId, rows, columns):
    request = []

    if columns > 25:
        print("########### Limiting number of columns to 25 from %d" % columns)
        columns = 25

    request.append({
      'addChart': {
        "chart": {
          "chartId": 3,
          "spec": {
            "title": "Topic Statistics (updated %s)" % datetime.datetime.now().strftime("%x"),
            "basicChart": {
              "chartType": "AREA",
              "stackedType": "STACKED",
              # "legendPosition": "BOTTOM_LEGEND",
              "axis": [
                {
                  "position": "BOTTOM_AXIS",
                  "title": "Upstream Release Tag"
                },
                {
                  "position": "LEFT_AXIS",
                  "title": "Patches"
                }
              ],
              "domains": [ scope("domain", sheetId, rows, 0) ],
              "series": sscope("series", sheetId, rows, 1, columns),
            }
          },
          "position": {
            "newSheet": True,
          }
        }
      }
    })

    response = doit(sheet, id, request)

    # Extract sheet Id from response
    reply = response.get('replies')
    sheetId = reply[0]['addChart']['chart']['position']['sheetId']

    request = [ ]
    request.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheetId,
                'title': 'Topic Statistics',
             },
             'fields': "title",
         }
    })
    doit(sheet, id, request)


def main():
    sheet = getsheet()
    id = init_spreadsheet(sheet)

    create_summary(sheet, id)
    topic_stats_sheet, topic_stats_rows, topic_stats_columns = create_topic_stats(sheet, id)

    add_backlog_chart(sheet, id)
    add_age_chart(sheet, id)
    add_stats_chart(sheet, id, topic_stats_sheet, topic_stats_rows, topic_stats_columns)

    move_sheet(sheet, id, 0, 4)
    hide_sheet(sheet, id, 0, True)

if __name__ == '__main__':
    main()
