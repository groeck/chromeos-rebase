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
from googleapiclient import discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import sqlite3
import os
import re
import time
from config import rebasedb, chromeos_path
from common import upstreamdb, rebase_baseline, rebase_target_tag, rebase_target_version

rebase_filename = "rebase-spreadsheet.id"

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

other_topic_id = 0 # Sheet Id to be used for "other" topic
have_other_topic = False

red = { 'red': 1, 'green': 0.4, 'blue': 0 }
yellow = { 'red': 1, 'green': 1, 'blue': 0 }
orange = { 'red': 1, 'green': 0.6, 'blue': 0 }
green = { 'red': 0, 'green': 0.9, 'blue': 0 }
blue = { 'red': 0.3, 'green': 0.6, 'blue': 1 }
white = { 'red': 1, 'green': 1, 'blue': 1 }

def get_other_topic_id():
    """ Calculate other_topic_id """

    global other_topic_id
    global have_other_topic

    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()

    c.execute("select topic, name from topics order by name")
    for topic, name in c.fetchall():
        if name == 'other':
            other_topic_id = topic
            have_other_topic = True
            conn.close()
            return
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

def doit(sheet, id, requests):
    body = {
        'requests': requests
    }

    request = sheet.batchUpdate(spreadsheetId=id, body=body)
    response = request.execute()

def delete_sheets(sheet, id, sheets):
    ''' Delete all sheets except sheet 0. In sheet 0, delete all values. '''
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
        with open(rebase_filename, 'r') as file:
            id = file.read()
        request = sheet.get(spreadsheetId=id, ranges = [ ], includeGridData=False)
        response = request.execute()
        sheets = response.get('sheets')
        delete_sheets(sheet, id, sheets)
    except:
        id = create_spreadsheet(sheet, 'Rebase %s -> %s' %
                                (rebase_baseline(), rebase_target_tag()))
        with open(rebase_filename, 'w') as file:
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

def add_topics_summary(requests):
    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()
    c2 = conn.cursor()
    version = rebase_target_version()
    counted_rows = 0

    c.execute("select topic, name from topics order by name")
    rowindex = 1
    for (topic, name) in c.fetchall():
        # Only add summary entry if there are commits touching this topic
        c2.execute("select disposition, reason from commits where topic=%d" % topic)
        rows = 0
        effrows = 0
        for (d, r) in c2.fetchall():
            # Skip entries associated with a topic if they are fully upstream
            # and are not being replaced.
            if d == 'drop' and r == 'upstream':
                continue
            rows += 1
            if d == 'pick':
                effrows += 1
        counted_rows += rows
        requests.append({
            'pasteData': {
                'data': '=HYPERLINK("#gid=%d","%s");%d;%d;;;;chromeos-%s-%s' %
                            (topic, name, rows, effrows, version,
                             name.replace('/','-')),
                'type': 'PASTE_NORMAL',
                'delimiter': ';',
                'coordinate': {
                    'sheetId': 0,
                    'rowIndex': rowindex
                }
            }
        })
        rowindex += 1

    allrows = 0
    c2.execute("select topic from commits where topic != 0")
    for r in c2.fetchall():
        allrows += 1

    # Now create an 'other' topic. We'll use it for unnamed topics.
    if not have_other_topic:
      requests.append({
        'pasteData': {
            'data': '=HYPERLINK("#gid=%d","other");%d;;;;;chromeos-%s-other' %
                             (other_topic_id, allrows - counted_rows, version),
            'type': 'PASTE_NORMAL',
            'delimiter': ';',
            'coordinate': {
                'sheetId': 0,
                'rowIndex': rowindex
            }
        }
      })

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

    add_sheet_header(requests, 0, 'Topic, Entries, Effective Entries, Owner, Reviewer, Status, Topic branch, Comments')

    # Now add all topics
    add_topics_summary(requests)

def add_description(requests):
    """ Add describing text to 'Summary' sheet """
    requests.append({
        'appendCells': {
            'sheetId': 0,
            'rows': [ { },
                { 'values': [
                    {'userEnteredValue': {'stringValue': 'Topic branch markers:'},
                    },
                 ]},
                { 'values': [
                    {'userEnteredValue': {'stringValue': 'blue'},
                      'userEnteredFormat': {
                            'backgroundColor': blue
                      }
                    },
                    {'userEnteredValue': {'stringValue':
                        'branch dropped: All patches upstream, no longer applicable, moved to another topic, or no longer needed' },
                    },
                 ]},
                { 'values': [
                    {'userEnteredValue': {'stringValue': 'green'},
                      'userEnteredFormat': {
                            'backgroundColor': green
                      }
                    },
                    {'userEnteredValue': {'stringValue':
                        'clean (no or minor conflicts)' },
                    },
                 ]},
                { 'values': [
                    {'userEnteredValue': {'stringValue': 'yellow'},
                      'userEnteredFormat': {
                            'backgroundColor': yellow
                      }
                    },
                    {'userEnteredValue': {'stringValue':
                        'mostly clean; problematic patches marked yellow' },
                    },
                 ]},
                { 'values': [
                    {'userEnteredValue': {'stringValue': 'orange'},
                      'userEnteredFormat': {
                            'backgroundColor': orange
                      }
                    },
                    {'userEnteredValue': {'stringValue':
                        'some problems; problematic patches marked orange' },
                    },
                 ]},
                { 'values': [
                    {'userEnteredValue': {'stringValue': 'red'},
                      'userEnteredFormat': {
                            'backgroundColor': red
                      }
                    },
                    {'userEnteredValue': {'stringValue':
                        'severe problems' },
                    },
                 ]},
            ],
            'fields': '*'
        }
    })

def addsheet(requests, index, topic, name):
    print('Adding sheet id=%d index=%d title="%s"' % (topic, index, name))

    requests.append({
        'addSheet': {
            'properties': {
                'sheetId': topic,
                'index': index,
                'title': name,
            }
        }
    })

    # Generate header row
    add_sheet_header(requests, topic, 'SHA, Description, Disposition, Comments')

def add_topics_sheets(requests):
    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()

    c.execute("select topic, name from topics order by name")

    index = 1
    for (topic, name) in c.fetchall():
        addsheet(requests, index, topic, name)
        index += 1

    # Add 'other' topic at the very end
    if not have_other_topic:
        addsheet(requests, index, other_topic_id, 'other')
    conn.close()

def add_sha(requests, sheet_id, sha, subject, disposition, reason, dsha, origin):
    comment = ""
    color = white

    if disposition == "replace" and dsha:
        comment = "with %s commit %s" % (origin, dsha)
        color = yellow
        if reason == "revisit":
            comment += " (revisit: imperfect match)"
            color = orange
    elif disposition == "drop":
        if reason == "revisit":
            color = red
            if dsha:
                comment = "revisit (imperfect match with %s commit %s)" % (origin, dsha)
            else:
                comment = "revisit (imperfect match)"
        elif reason == "upstream/fixup":
            color = yellow
            comment = "fixup of upstream patch %s" % dsha
        elif reason == "upstream/match":
            color = yellow
            comment = "%s commit %s" % (origin, dsha)
        elif reason == "revisit/fixup":
            color = yellow
            comment = "fixup of %s commit %s" % (origin, dsha)
        else:
            color = yellow
            if dsha:
                comment = "%s (%s commit %s)" % (reason, origin, dsha)
            else:
                comment = reason

    print("Adding sha %s (%s) to sheet ID %d" % (sha, subject, sheet_id))

    requests.append({
        'appendCells': {
            'sheetId': sheet_id,
            'rows': [
                { 'values': [
                    {'userEnteredValue': {'stringValue': sha},
                      'userEnteredFormat': {
                            'backgroundColor': color
                      }
                    },
                    {'userEnteredValue': {'stringValue': subject},
                      'userEnteredFormat': {
                            'backgroundColor': color
                      }
                    },
                    {'userEnteredValue': {'stringValue': disposition},
                      'userEnteredFormat': {
                            'backgroundColor': color
                      }
                    },
                    {'userEnteredValue': {'stringValue': comment},
                      'userEnteredFormat': {
                            'backgroundColor': color
                      }
                    },
                ]}
            ],
            'fields': '*'
        }
    })

def add_commits(requests):
    conn = sqlite3.connect(rebasedb)
    uconn = sqlite3.connect(upstreamdb)
    c = conn.cursor()
    c2 = conn.cursor()
    cu = uconn.cursor()

    sheets = set([ ])

    c.execute("select sha, dsha, subject, disposition, reason, topic from commits where topic > 0")
    for (sha, dsha, subject, disposition, reason, topic) in c.fetchall():
        # Skip entries associated with a topic if they are fully upstream
        # and are not being replaced.
        if disposition == 'drop' and reason == 'upstream':
            continue
        c2.execute("select topic, name from topics where topic=%d" % topic)
        if c2.fetchone():
            sheet_id = topic
        else:
            sheet_id = other_topic_id

        cu.execute("select sha from commits where sha='%s'" % dsha)
        if cu.fetchone():
          origin = 'upstream'
        else:
          origin = 'linux-next'
        sheets.add(sheet_id)
        add_sha(requests, sheet_id, sha, subject, disposition, reason, dsha, origin)

    for s in sheets:
        resize_sheet(requests, s, 0, 4)

def main():
    sheet = getsheet()
    id = init_spreadsheet(sheet)
    get_other_topic_id()

    requests = [ ]
    create_summary(requests)
    add_topics_sheets(requests)
    doit(sheet, id, requests)
    requests = [ ]
    add_commits(requests)
    # Now auto-resize columns A, B, C, and G in Summary sheet
    resize_sheet(requests, 0, 0, 3)
    resize_sheet(requests, 0, 6, 7)
    # Add description after resizing
    add_description(requests)
    doit(sheet, id, requests)

if __name__ == '__main__':
    main()
