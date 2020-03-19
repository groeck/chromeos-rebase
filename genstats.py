#!/usr/bin/env python2
#/usr/bin/env python3

# Use information in rebase database to create rebase spreadsheet
# Required python modules:
# google-api-python-client google-auth-httplib2 google-auth-oauthlib
#
# The Google Sheets API needs to be enabled to run this script.
# Also, you'll need to generate access credentials and store those
# in credentials.json.

from __future__ import print_function
import pickle
import os.path
import re
from googleapiclient import discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import sqlite3
import os
import re
import subprocess
import time
from config import rebasedb, \
        stable_path, android_path, chromeos_path, \
        rebase_target
from common import upstreamdb, rebase_baseline

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

rp = re.compile("(CHROMIUM: *|CHROMEOS: *|UPSTREAM: *|FROMGIT: *|FROMLIST: *|BACKPORT: *)+(.*)")

other_topic_id = 0 # Sheet Id to be used for "other" topic

red = { 'red': 1, 'green': 0.4, 'blue': 0 }
yellow = { 'red': 1, 'green': 1, 'blue': 0 }
orange = { 'red': 1, 'green': 0.6, 'blue': 0 }
green = { 'red': 0, 'green': 0.9, 'blue': 0 }
blue = { 'red': 0.3, 'green': 0.6, 'blue': 1 }
white = { 'red': 1, 'green': 1, 'blue': 1 }

lastrow = 0

def get_other_topic_id():
    """ Calculate other_topic_id """

    global other_topic_id

    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()

    c.execute("select topic from topics order by name")
    for (topic,) in c.fetchall():
        if topic >= other_topic_id:
            other_topic_id = topic + 1

    conn.close()

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

def NOW():
  return int(time.time())

def add_topics_summary_row(requests, conn, rowindex, topic, name):
    c = conn.cursor()
    c2 = conn.cursor()
    version = rebase_target.strip('v')

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

    # Only add summary entry if there are commits associated with this topic
    if rows:
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
    return rows

def NOW():
  return int(time.time())

def add_topics_summary(requests):
    global lastrow
    global other_topic_id

    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()
    version = rebase_target.strip('v')

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

def create_summary(requests):
    requests.append({
        'updateSheetProperties': {
            # 'sheetId': 0,
            'properties': {
                'title': 'Summary',
            },
            'fields': 'title'
        }
    })

    #requests.append({
    #    'appendCells': {
    #        'sheetId': 0,
    #        'rows': [
#                { 'values': [
#                    {"userEnteredValue": {"stringValue": "Topic"}},
#                    {"userEnteredValue": {"stringValue": "Entries"}},
#                    {"userEnteredValue": {"stringValue": "Owner"}},
#                    {"userEnteredValue": {"stringValue": "Reviewer"}},
#                    {"userEnteredValue": {"stringValue": "Status"}},
#                    {"userEnteredValue": {"stringValue": "Topic branch"}},
#                    {"userEnteredValue": {"stringValue": "Comments"}}
#                ]}
#            ],
#            "fields": "*"
#        }
#    })

    # add_sheet_header(requests, 0, 'Topic, Average age (days), Entries, Net Entries, Upstream, Backport, Fromgit, Fromlist, Chromium, Untagged/Unknown')
    add_sheet_header(requests, 0, 'Topic, Upstream, Backport, Fromgit, Fromlist, Chromium, Untagged/Unknown, Net, Total, Average Age (days)')

    # Now add all topics
    add_topics_summary(requests)

def doit(sheet, id, requests):
    body = {
        'requests': requests
    }

    request = sheet.batchUpdate(spreadsheetId=id, body=body)
    response = request.execute()
    return response

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
            "title": "Upstream Backlog",
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
              "series": [
                  scope("series", 0, lastrow + 1, 1),
                  scope("series", 0, lastrow + 1, 2),
                  scope("series", 0, lastrow + 1, 3),
                  scope("series", 0, lastrow + 1, 4),
                  scope("series", 0, lastrow + 1, 5),
                  scope("series", 0, lastrow + 1, 6)
              ]
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

    # chart start with summary row 2. Row 1 is assumed to be 'chromeos'
    # which is not counted as backlog.
    request.append({
      'addChart': {
        "chart": {
          "chartId": 2,
          "spec": {
            "title": "Upstream Backlog Age",
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
                  "title": "Average Age"
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

def main():
    sheet = getsheet()
    id = create_spreadsheet(sheet, 'Backlog Statistics for chromeos-%s' % rebase_baseline().strip('v'))
    get_other_topic_id()

    requests = [ ]
    create_summary(requests)
    doit(sheet, id, requests)
    requests = [ ]
    # Now auto-resize columns A, B, C, in Summary sheet
    resize_sheet(requests, 0, 0, 10)
    doit(sheet, id, requests)
    add_backlog_chart(sheet, id)
    add_age_chart(sheet, id)

if __name__ == '__main__':
    main()
