# main.py

import os
import time
import threading
import json
from tasks import TASK_NAMES, app  # Importing TASK_NAMES and app from tasks.py
from autoscaler import Autoscaler
from utils.monitoring import get_queue_length
from utils.db import init_db, save_result
from utils.data_models import ProjectData, KnowledgeGraph, ChunkerConfig, LLMConfig
from kombu import Queue


def calculate_desired_containers(queue_length):

    MAX_TASKS_PER_CONTAINER = 5
    return (queue_length // MAX_TASKS_PER_CONTAINER)
    return (queue_length // MAX_TASKS_PER_CONTAINER)


def monitor_and_scale():
    autoscaler = Autoscaler()
    while True:
        for tool, task_name in TASK_NAMES.items():
            # Assuming only 'llm' tasks require autoscaling
            if tool == "llm":
                queue_length = get_queue_length(tool)
                desired_containers = calculate_desired_containers(queue_length)
                image_name = os.environ.get("DOCKER_IMAGE_LLM", "llm")
                autoscaler.scale_containers(desired_containers, image_name)
        time.sleep(10)  # Adjust the sleep time as needed



# In main.py, modify run_test()
def run_test():
    print("Starting GAIA communication test...")
    
    # Create test ProjectData object with minimal test data
    test_data = ProjectData(
        domain="test_domain",
        docsSource="/app/data",  # Path to the directory containing test_doc.txt
        textData="Test document 1. Test document 2. Test document 3.",  # Simple sentences for NLTK
        queries=["What are the main topics?"],
        status="processing"
    )
    
    # Initialize nested objects with test data
    test_data.kg = KnowledgeGraph(
        kgTriples=["entity1 - relation1 - entity2"],
        ner=["Test"]
    )
    test_data.chunker = ChunkerConfig(
        chunkingMethod="fixed_size",
        chunks=[]
    )
    test_data.llm = LLMConfig(
        llm="test_model"
    )
    
    results = {}
    task_states = {}
    
    # Send relevant parts of the ProjectData to each tool
    tool_data_mapping = {
        "chunker": {
            "docsSource": test_data.docsSource,  # Pass the directory path
            "chunkingMethod": test_data.chunker.chunkingMethod
        },
        "vector_db": {
            "textData": test_data.textData,
            "embedding": test_data.embedding,
            "vectorDB": test_data.vectorDB
        },
        "graph_db": {
            "textData": test_data.textData,
            "queries": test_data.queries
        },
        "llm": {
            "textData": test_data.textData,
            "queries": test_data.queries,
            "llm": test_data.llm.llm
        },
        "prompt": {
            "textData": test_data.textData,
            "queries": test_data.queries,
            "kg": test_data.kg.to_dict()
        }
    }
    
    for tool, task_name in TASK_NAMES.items():
        print(f"Sending task to {tool}...")
        tool_specific_data = tool_data_mapping.get(tool, {})
        
        try:
            task = app.send_task(task_name, args=[json.dumps(tool_specific_data)], queue=tool)
            results[tool] = task
            task_states[tool] = 'PENDING'
            print(f"Successfully sent task to {tool}")
        except Exception as e:
            print(f"Error sending task to {tool}: {str(e)}")
            task_states[tool] = 'ERROR'
            continue
    
    # Collect and update results
    for tool, task in results.items():
        try:
            task_states[tool] = 'PROCESSING'
            result = task.get(timeout=60)
            task_states[tool] = 'COMPLETED'
            
            # Update the ProjectData object with the results
            if tool == "chunker":
                test_data.chunker.chunks = json.loads(result).get("chunks", [])
            elif tool == "vector_db":
                test_data.vectorDBLoaded = json.loads(result).get("loaded", False)
            elif tool == "graph_db":
                kg_result = json.loads(result)
                test_data.kg.kgTriples = kg_result.get("kgTriples", [])
                test_data.kg.ner = kg_result.get("ner", [])
            elif tool == "llm":
                test_data.llm.llmResult = json.loads(result).get("llmResult", "")
            
            results[tool] = result
            save_result(tool, json.dumps(tool_specific_data), result)
            
        except Exception as e:
            task_states[tool] = 'FAILED'
            print(f"Error getting result from {tool}: {str(e)}")
            results[tool] = f"Error: {str(e)}"
            save_result(tool, json.dumps(tool_specific_data), f"Error: {str(e)}")
    
    return test_data.to_dict(), task_states


def wait_for_services():
    max_retries = 30
    retry_interval = 5
    
    for _ in range(max_retries):
        try:
            # Try to connect to RabbitMQ
            connection = app.connection()
            connection.connect()
            connection.release()
            print("Successfully connected to RabbitMQ")
            return True
        except Exception as e:
            print(f"Waiting for services to be ready... {str(e)}")
            time.sleep(retry_interval)
    
    raise Exception("Services failed to become ready")


def wait_for_rabbitmq():
    """Wait for RabbitMQ to be ready and ensure queues are declared."""
    print("Waiting for RabbitMQ...")
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            # Try to connect and declare queues
            with app.connection_for_write() as conn:
                channel = conn.channel()
                for queue_name in TASK_NAMES.keys():
                    Queue(queue_name, channel=channel, durable=True).declare()
            print("RabbitMQ is ready!")
            return True
        except Exception as e:
            print(f"Waiting for RabbitMQ... Attempt {i+1}/{max_retries}")
            time.sleep(retry_interval)
    
    raise Exception("RabbitMQ connection failed after maximum retries")


if __name__ == "__main__":
    # Wait for services to be ready
    wait_for_services()
    
    # Wait for RabbitMQ and declare queues
    wait_for_rabbitmq()
    
    # Initialize the database
    init_db()
    
    # Start the monitoring thread
    monitor_thread = threading.Thread(target=monitor_and_scale, daemon=True)
    monitor_thread.start()
    
    # Run the test
    run_test()