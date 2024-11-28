import sqlite3
import os

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect('data/results.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS task_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tool TEXT,
                  input TEXT,
                  output TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_result(tool, input_data, output):
    conn = sqlite3.connect('data/results.sqlite')
    c = conn.cursor()
    c.execute("INSERT INTO task_results (tool, input, output) VALUES (?, ?, ?)",
              (tool, input_data, output))
    conn.commit()
    conn.close()