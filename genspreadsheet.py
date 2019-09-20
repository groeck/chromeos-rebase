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
import subprocess
import time
from config import rebasedb, \
        stable_path, android_path, chromeos_path, \
        rebase_baseline, stable_baseline, rebase_target

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

other_topic_id = 0 # Sheet Id to be used for "other" topic

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

def add_topics_summary(requests):
    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()
    c2 = conn.cursor()
    version = rebase_target.strip('v')
    counted_rows = 0

    c.execute("select topic, name from topics order by name")
    rowindex = 1
    for (topic, name) in c.fetchall():
        # Only add summary entry if there are commits touching this topic
        c2.execute("select topic from commits where topic=%d" % topic)
        rows = 0
        for r in c2.fetchall():
            rows += 1
        counted_rows += rows
        requests.append({
            'pasteData': {
                'data': '=HYPERLINK("#gid=%d","%s");%d;;;;chromeos-%s-%s' %
                            (topic, name, rows, version,
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
    requests.append({
        'pasteData': {
            'data': '=HYPERLINK("#gid=%d","other");%d;;;;chromeos-%s-other' %
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

    add_sheet_header(requests, 0, 'Topic, Entries, Owner, Reviewer, Status, Topic branch, Comments')

    # Now add all topics
    add_topics_summary(requests)

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
    addsheet(requests, index, other_topic_id, 'other')
    conn.close()

def add_sha(requests, sheet_id, sha, subject, disposition, dsha):
    comment = ""
    if disposition =="replace" and dsha:
        comment = "with %s" % dsha

    print("Adding sha %s (%s) to sheet ID %d" % (sha, subject, sheet_id))

    requests.append({
        'appendCells': {
            'sheetId': sheet_id,
            'rows': [
                { 'values': [
                    {'userEnteredValue': {'stringValue': sha}},
                    {'userEnteredValue': {'stringValue': subject}},
                    {'userEnteredValue': {'stringValue': disposition}},
                    {'userEnteredValue': {'stringValue': comment}},
                ]}
            ],
            'fields': '*'
        }
    })

def add_commits(requests):
    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()
    c2 = conn.cursor()

    sheets = set([ ])

    c.execute("select sha, dsha, subject, disposition, topic from commits where topic > 0")
    for (sha, dsha, subject, disposition, topic) in c.fetchall():
        c2.execute("select topic, name from topics where topic=%d" % topic)
        if c2.fetchone():
            sheet_id = topic
        else:
            sheet_id = other_topic_id

        sheets.add(sheet_id)
        add_sha(requests, sheet_id, sha, subject, disposition, dsha)

    for s in sheets:
        resize_sheet(requests, s, 0, 4)

    # Now auto-resize columns A, B, and F in Summary sheet
    resize_sheet(requests, 0, 0, 2)
    resize_sheet(requests, 0, 5, 6)

def doit(sheet, id, requests):
    body = {
        'requests': requests
    }

    request = sheet.batchUpdate(spreadsheetId=id, body=body)
    response = request.execute()

def main():
    sheet = getsheet()
    id = create_spreadsheet(sheet, 'Rebase %s -> %s' % (rebase_baseline,
                                                        rebase_target))
    get_other_topic_id()

    requests = [ ]
    create_summary(requests)
    add_topics_sheets(requests)
    doit(sheet, id, requests)
    requests = [ ]
    add_commits(requests)
    doit(sheet, id, requests)

if __name__ == '__main__':
    main()
