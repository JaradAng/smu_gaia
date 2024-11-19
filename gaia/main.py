# main.py

import os
import time
import threading
import json
from tasks import TASK_NAMES, app  # Importing TASK_NAMES and app from tasks.py
from autoscaler import Autoscaler
from utils.monitoring import get_queue_length
from utils.db import init_db, save_result
from utils.data_models import ProjectData


def calculate_desired_containers(queue_length):

    MAX_TASKS_PER_CONTAINER = 5
    return (queue_length // MAX_TASKS_PER_CONTAINER) + 1


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
    
    # Create test ProjectData object
    test_data = ProjectData(
        domain="test_domain",
        docsSource="test_source",
        textData="The species of elephants is well known in the safari. Although they can withstand long droughts, their skin requires contant moisture.",
        queries=["What is the main topic of this document?"],
        embedding="test_embedding",
        vectorDB="test_vectordb"
    )
    
    results = {}
    task_states = {}
    
    # Send relevant parts of the ProjectData to each tool
    tool_data_mapping = {
        "chunker": {
            "textData": test_data.textData,
            "chunkingMethod": "paragraph"
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
            "queries": test_data.queries
        },
        "prompt": {
            "textData": test_data.textData,
            "queries": test_data.queries,
            "kg": test_data.kg.to_dict() if test_data.kg else None
        }
    }
    
    for tool, task_name in TASK_NAMES.items():
        print(f"Sending task to {tool}...")
        tool_specific_data = tool_data_mapping.get(tool, {})
        task = app.send_task(task_name, args=[json.dumps(tool_specific_data)], queue=tool)
        results[tool] = task
        task_states[tool] = 'PENDING'
    
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


if __name__ == "__main__":
    # Wait for RabbitMQ and other services to be ready
    time.sleep(10)
    init_db()

    # Start autoscaling in a separate thread
    threading.Thread(target=monitor_and_scale, daemon=True).start()

    # Run the test
    run_test()