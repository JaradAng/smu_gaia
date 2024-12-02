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
from celery import Celery

# Configure Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_heartbeat=60,
    broker_pool_limit=10,
    broker_transport_options={
        'confirm_publish': True,
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    }
)

# Configure task routes
app.conf.task_routes = {
    'chunker': {'queue': 'chunker'},
    'graph_db': {'queue': 'graph_db'},
    'llm': {'queue': 'llm'}
}

# Configure task settings
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True
)

def calculate_desired_containers(queue_length):

    MAX_TASKS_PER_CONTAINER = 5
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
    """Run test with the specified configuration."""
    results = {}
    task_states = {}
    
    try:
        # Initialize test data
        test_data = ProjectData(
            domain="fantasy",
            docsSource="/shared_data",  
            queries=["What is the main quest of Thorin Ironfist?"],
            status="processing"
        )
        
        # Initialize nested objects
        test_data.kg = KnowledgeGraph(kgTriples=[], ner=[])
        test_data.chunker = ChunkerConfig(
            chunkingMethod="sentence_based",
            chunks=[]
        )
        test_data.llm = LLMConfig(llm="bert-base-uncased")
        
        # Send to chunker
        chunker_data = {
            "docsSource": test_data.docsSource,
            "chunkingMethod": test_data.chunker.chunkingMethod
        }
        print(f"Sending data to chunker: {json.dumps(chunker_data, indent=2)}")
        results["chunker"] = app.send_task(TASK_NAMES["chunker"], args=[json.dumps(chunker_data)], queue="chunker")
        task_states["chunker"] = 'PENDING'
        
        # Send to graph_db (independent of chunker)
        graph_data = {
            "docsSource": test_data.docsSource,  # Using same source as chunker
            "queries": test_data.queries
        }
        print(f"Sending data to graph_db: {json.dumps(graph_data, indent=2)}")
        results["graph_db"] = app.send_task(
            TASK_NAMES["graph_db"], 
            args=[json.dumps(graph_data)], 
            queue="graph_db",
            retry=True,
            retry_policy={
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.5,
            }
        )
        task_states["graph_db"] = 'PENDING'
        
        try:
            # Process chunker results
            initial_chunker_result, final_chunker_result = results["chunker"].get(timeout=240)
            initial_chunker_dict = json.loads(initial_chunker_result)
            final_chunker_dict = json.loads(final_chunker_result)
            test_data.chunker.chunks = final_chunker_dict.get("chunks", [])
            
        except Exception as e:
            print(f"Error processing chunker response: {str(e)}")
            task_states["chunker"] = 'FAILED'
            # Continue execution as graph_db is independent
        
        # Continue with other tasks
        prompt_data = {
            "queries": test_data.queries,
            "waitForKG": True  
        }
        print(f"Sending data to prompt: {json.dumps(prompt_data, indent=2)}")
        results["prompt"] = app.send_task(TASK_NAMES["prompt"], args=[json.dumps(prompt_data)], queue="prompt")
        task_states["prompt"] = 'PENDING'
        
        llm_data = {
            "queries": test_data.queries,
            "llm": test_data.llm.llm,
            "waitForPrompts": True  
        }
        print(f"Sending data to llm: {json.dumps(llm_data, indent=2)}")
        results["llm"] = app.send_task(TASK_NAMES["llm"], args=[json.dumps(llm_data)], queue="llm")
        task_states["llm"] = 'PENDING'
        
        # Collect results with individual timeouts
        for tool, task in results.items():
            if tool == "chunker":  # Skip chunker as we already handled it
                continue
            try:
                task_states[tool] = 'PROCESSING'
                result = task.get(timeout=240)  # 2 minutes timeout per task
                result_dict = json.loads(result)
                task_states[tool] = 'COMPLETED'
                print(f"Received result from {tool}: {json.dumps(result_dict, indent=2)}")
                
                # Update ProjectData based on tool results
                if tool == "graph_db":
                    test_data.kg.kgTriples = result_dict.get("kgTriples", [])
                    test_data.kg.ner = result_dict.get("ner", [])
                elif tool == "prompt":
                    test_data.prompts = result_dict
                elif tool == "llm":
                    test_data.llm.llmResult = result_dict.get("llmResult", "")
                
                save_result(tool, json.dumps(llm_data), result)
                
            except Exception as e:
                task_states[tool] = 'FAILED'
                print(f"Error processing {tool}: {str(e)}")
                save_result(tool, json.dumps(llm_data), f"Error: {str(e)}")
                
    except Exception as e:
        print(f"Error initiating tasks: {str(e)}")
        return test_data.to_dict(), task_states
    
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
                conn.ensure_connection(max_retries=3)  # Ensure connection is established
                channel = conn.channel()
                # Declare queues with more durable settings
                for queue_name in TASK_NAMES.keys():
                    queue = Queue(
                        queue_name,
                        channel=channel,
                        durable=True,
                        auto_delete=False,
                        arguments={'x-queue-type': 'classic'}
                    )
                    queue.declare()
                    print(f"Declared queue: {queue_name}")
            print("RabbitMQ is ready!")
            return True
        except Exception as e:
            print(f"Waiting for RabbitMQ... Attempt {i+1}/{max_retries}. Error: {str(e)}")
            if i == max_retries - 1:
                print("Detailed connection error:", str(e))
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