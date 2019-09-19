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

def getsheet():
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
    spreadsheet = {
        'properties': {
            'title': title
        }
    }

    request = sheet.create(body=spreadsheet, fields='spreadsheetId')
    response = request.execute()
    return response.get('spreadsheetId')

def add_topics_summary(sheet, id, requests):
    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()
    version = rebase_target.strip('v')

    c.execute("select topic, name from topics order by name")
    rowindex = 1
    for (topic, name) in c.fetchall():
        requests.append({
            'pasteData': {
                'data': '%s,,,,chromeos-%s-%s' %
                            (name, version,
                             name.replace('/','-')),
                'type': 'PASTE_NORMAL',
                'delimiter': ',',
                'coordinate': {
                    'sheetId': 0,
                    'rowIndex': rowindex
                }
            }
        })
        rowindex += 1

    # Finally create an 'others' topic. We'll use it for unnamed topics.
    requests.append({
        'pasteData': {
            'data': 'other,,,,chromeos-%s-other' % version,
            'type': 'PASTE_NORMAL',
            'delimiter': ',',
            'coordinate': {
                'sheetId': 0,
                'rowIndex': rowindex
            }
        }
    })

    conn.close()

def add_sheet_header(requests, id, fields):
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

    add_sheet_header(requests, 0, 'Topic, Owner, Reviewer, Status, Topic branch, Comments')

    # Now add all topics
    add_topics_summary(sheet, id, requests)

    body = {
        'requests': requests
    }

    request = sheet.batchUpdate(spreadsheetId=id, body=body)
    response = request.execute()

def addsheet(sheet, id, index, topic, name):
    requests = [ ]

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

    body = {
            'requests': requests
    }

    request = sheet.batchUpdate(spreadsheetId=id, body=body)
    response = request.execute()

def add_topics_sheets(sheet, id):
    conn = sqlite3.connect(rebasedb)
    c = conn.cursor()
    c2 = conn.cursor()

    c.execute("select topic, name from topics order by name")

    # Add "other" topic at the very end
    other = 0
    index = 1
    for (topic, name) in c.fetchall():
        addsheet(sheet, id, index, topic, name)
	if topic >= other:
	    other = topic + 1
	index += 1

    addsheet(sheet, id, index, other, "other")

    # Now go through all commits and add to spreadsheets

    conn.close()

def main():
    sheet = getsheet()
    id = create_spreadsheet(sheet, 'Rebase %s -> %s' % (rebase_baseline,
                                                        rebase_target))
    create_summary(sheet, id)
    add_topics_sheets(sheet, id)

if __name__ == '__main__':
    main()
