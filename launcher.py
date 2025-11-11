import os
import sqlite3
import subprocess

DB_FILE = "database.db"

def is_corrupted(db_file):
    if not os.path.exists(db_file):
        return False
    try:
        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA schema_version;")
        conn.close()
        return False
    except sqlite3.DatabaseError:
        return True

if is_corrupted(DB_FILE):
    print(f"⚠️ {DB_FILE} is corrupted. Deleting...")
    os.remove(DB_FILE)
elif os.path.exists(DB_FILE):
    print(f"ℹ️ {DB_FILE} exists. Keeping it.")

print("🚀 Starting Flask app...")
subprocess.run(["python", "app.py"])
