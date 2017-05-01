import sqlite3
import os
import subprocess

dbname = "drop49.db"

try:
    os.remove(dbname)
except:
    pass

conn = sqlite3.connect(dbname)

c = conn.cursor()

# Create tables
c.execute("CREATE TABLE droplist (sha text, resolution text, reason text, dsha text)")
c.execute("CREATE UNIQUE INDEX drop_sha ON droplist (sha)")

conn.commit()
conn.close()
