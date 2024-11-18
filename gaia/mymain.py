import json
from typing import Dict, Any
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
    'graph_db': 'graph_db_task'
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

def get_test_data() -> Dict[str, Any]:
    """
    Returns the test JSON data structure.
    """
    return {
        "id": "proj_2024_03_30_001",
        "domain": "healthcare_research",
        "docsSource": "pubmed_articles",
        "queries": [
            "What are the latest treatments for type 2 diabetes?",
            "How does metformin affect blood glucose levels?",
            "What are the common side effects of diabetes medications?"
        ],
        "textData": "Type 2 diabetes is a chronic condition that affects the way your body metabolizes sugar (glucose). With type 2 diabetes, your body either resists the effects of insulin — a hormone that regulates the movement of sugar into your cells — or doesn't produce enough insulin to maintain normal glucose levels...",
        "embedding": "text-embedding-ada-002",
        "vectorDB": "pinecone",
        "ragText": "Based on the retrieved information, type 2 diabetes treatments include lifestyle modifications such as diet and exercise, along with medications like metformin, sulfonylureas, and newer drug classes such as GLP-1 receptor agonists...",
        "kg": {
            "kgTriples": [
                "Type2Diabetes|affects|glucose_metabolism",
                "Metformin|treats|Type2Diabetes",
                "Type2Diabetes|requires|insulin_regulation",
                "Insulin|regulates|blood_glucose",
                "GLP1_agonists|improve|glucose_control"
            ],
            "ner": [
                "DISEASE: Type 2 diabetes",
                "MEDICATION: metformin",
                "CHEMICAL: glucose",
                "PROTEIN: insulin",
                "DRUG_CLASS: GLP-1 receptor agonists"
            ]
        },
        "chunker": {
            "chunkingMethod": "recursive_text_splitter",
            "chunks": [
                "Type 2 diabetes is a chronic condition that affects the way your body metabolizes sugar (glucose).",
                "With type 2 diabetes, your body either resists the effects of insulin or doesn't produce enough insulin.",
                "Maintaining normal glucose levels is essential for managing type 2 diabetes."
            ]
        },
        "llm": {
            "llm": "gpt-4",
            "llmResult": "Based on the analysis of recent medical literature, the management of type 2 diabetes involves a multi-faceted approach. First-line treatment typically includes metformin, which works by improving insulin sensitivity and reducing glucose production in the liver..."
        },
        "vectorDBLoaded": True,
        "similarityIndices": {
            "cosine": 0.87,
            "euclidean": 0.92,
            "manhattan": 0.85
        },
        "generatedResponse": "According to current medical research, the treatment of type 2 diabetes involves both medication and lifestyle changes. Metformin remains the primary first-line medication, working to improve insulin sensitivity and reduce glucose production. Recent studies have shown promising results with GLP-1 receptor agonists, which not only help control blood sugar but may also contribute to weight loss. Regular monitoring of blood glucose levels and appropriate medication adjustment are essential for optimal disease management."
    }

def run_test():
    print("Starting GAIA communication test...")
    
    test_data = get_test_data()
    results = {}

    for tool, task_name in TASK_NAMES.items():
        print(f"Sending task to {tool}...")
        #  queue routing
        try:
            json_data = json.dumps(test_data)
            task = app.send_task(task_name, args=[json_data], queue=tool)
            result = task.get(timeout=30)  

            # Parse result if it's JSON
            try:
                if isinstance(result, str):
                    result = json.loads(result)
            except json.JSONDecodeError:
                pass  # Keep result as is if it's not JSON
            
            results[tool] = result
            save_result(tool, test_data, result)
        except json.JSONDecodeError as e:
            error_msg = f"Error encoding test data: {str(e)}"
            results[tool] = error_msg
            save_result(tool, test_data, error_msg)
            
        except Exception as e:
            error_msg = f"Error processing task: {str(e)}"
            results[tool] = error_msg
            save_result(tool, test_data, error_msg)

    print("\nTest Results:")
    for tool, result in results.items():
        print(f"{tool}: {result}")

    print("\nGAIA communication test completed.")

if __name__ == "__main__":
    # Wait for RabbitMQ and other services to be ready
    time.sleep(10)
    init_db()
    run_test()
