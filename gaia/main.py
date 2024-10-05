from celery import Celery
from kombu import Queue  
import os
import time
import sqlite3


app = Celery('gaia', 
             broker=os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//'),
             backend='db+sqlite:///data/results.sqlite')

# Setup routing keys
app.conf.task_queues = (
    Queue('chunker', routing_key='chunker'),
    Queue('vector_db', routing_key='vector_db'),
    Queue('graph_db', routing_key='graph_db'),
    Queue('llm', routing_key='llm'),
    Queue('prompt', routing_key='prompt')
)

TASK_NAMES = {
    'chunker': 'chunker_task',
    'vector_db': 'vector_db_task',
    'graph_db': 'graph_db_task',
    'llm': 'llm_task',
    'prompt': 'prompt_task'
}

def init_db():
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

def run_test():
    print("Starting GAIA communication test...")
    
    test_data = "This is a test message from GAIA"
    results = {}

    for tool, task_name in TASK_NAMES.items():
        print(f"Sending task to {tool}...")
        #  queue routing
        task = app.send_task(task_name, args=[test_data], queue=tool)
        try:
            result = task.get(timeout=30)  
            results[tool] = result
            save_result(tool, test_data, result)
        except Exception as e:
            print(f"Error getting result from {tool}: {str(e)}")
            results[tool] = f"Error: {str(e)}"
            save_result(tool, test_data, f"Error: {str(e)}")

    print("\nTest Results:")
    for tool, result in results.items():
        print(f"{tool}: {result}")

    print("\nGAIA communication test completed.")

if __name__ == "__main__":
    # Wait for RabbitMQ and other services to be ready
    time.sleep(10)
    init_db()
    run_test()
