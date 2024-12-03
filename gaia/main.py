# main.py

import os
import time
import threading
import json
import logging
from tasks import TASK_NAMES, app, wait_for_rabbitmq  # Import wait_for_rabbitmq from tasks.py
from autoscaler import Autoscaler
from utils.monitoring import get_queue_length
from utils.db import init_db, save_result
from utils.data_models import ProjectData, KnowledgeGraph, ChunkerConfig, LLMConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def monitor_and_scale():
    """Monitor queue lengths and scale workers accordingly."""
    autoscaler = Autoscaler()
    while True:
        for queue_name in ["llm", "chunker"]:  # Add more queues as needed
            queue_length = get_queue_length(queue_name)
            logger.info(f"Queue {queue_name} length: {queue_length}")
            autoscaler.scale_containers(queue_length, queue_name)
        time.sleep(30)  # Check every 30 seconds

def wait_for_services():
    """Wait for required services to be ready."""
    logger.info("Waiting for services to be ready...")
    # Add any additional service checks here
    pass

def run_test():
    """Run a test workflow through the system."""
    logger.info("Starting test workflow...")
    
    # Initialize test data with required arguments
    test_data = ProjectData(
        domain="test",
        docsSource="/shared_data"
    )
    test_data.queries = ["What is the main quest of Thorin Ironfist?"]
    
    # Track task states and results
    results = {}
    task_states = {}
    
    try:
        # Prepare data for each task
        chunker_data = {
            "docsSource": test_data.docsSource,
            "chunkingMethod": "sentence_based"
        }
        
        graph_data = {
            "docsSource": test_data.docsSource,
            "queries": test_data.queries
        }
        
        prompt_data = {
            "queries": test_data.queries,
            "waitForKG": True
        }
        
        # Send tasks to respective queues
        logger.info(f"Sending data to chunker: {json.dumps(chunker_data, indent=2)}")
        results["chunker"] = app.send_task(
            TASK_NAMES["chunker"],
            args=[json.dumps(chunker_data)],
            queue="chunker"
        )
        task_states["chunker"] = 'PENDING'
        
        logger.info(f"Sending data to graph_db: {json.dumps(graph_data, indent=2)}")
        results["graph_db"] = app.send_task(
            TASK_NAMES["graph_db"],
            args=[json.dumps(graph_data)],
            queue="graph_db"
        )
        task_states["graph_db"] = 'PENDING'
        
        # Process results and send dependent tasks
        try:
            graph_db_result = results["graph_db"].get(timeout=240)
            graph_db_dict = json.loads(graph_db_result)
            test_data.kg.kgTriples = graph_db_dict.get("kgTriples", [])
            test_data.kg.ner = graph_db_dict.get("ner", [])
            task_states["graph_db"] = 'COMPLETED'
            logger.info("Graph DB task completed successfully")
            
            # Send prompt task after graph_db completes
            logger.info(f"Sending data to prompt: {json.dumps(prompt_data, indent=2)}")
            results["prompt"] = app.send_task(
                TASK_NAMES["prompt"],
                args=[json.dumps(prompt_data)],
                kwargs={"wait_for_kg": True, "wait_for_prompts": False},
                queue="prompt"
            )
            task_states["prompt"] = 'PENDING'
            
            # Process prompt results and send LLM task
            prompt_result = results["prompt"].get(timeout=240)
            prompt_dict = json.loads(prompt_result)
            test_data.prompts = prompt_dict.get("prompts", {})
            task_states["prompt"] = 'COMPLETED'
            logger.info("Prompt task completed successfully")
            
            # Prepare LLM data using the processed prompts
            llm_data = {
                "queries": test_data.prompts.get("processedQueries", []),  # Use processed queries
                "llm": "bert-base-uncased",
                "waitForPrompts": True
            }
            
            logger.info(f"Sending data to llm: {json.dumps(llm_data, indent=2)}")
            results["llm"] = app.send_task(
                TASK_NAMES["llm"],
                args=[json.dumps(llm_data)],
                kwargs={"wait_for_prompts": True},
                queue="llm"
            )
            task_states["llm"] = 'PENDING'
            
        except Exception as e:
            logger.error(f"Error processing graph_db: {str(e)}")
            task_states["graph_db"] = 'FAILED'
        
        # Process remaining results
        try:
            llm_result = results["llm"].get(timeout=240)
            llm_dict = json.loads(llm_result)
            test_data.llm = llm_dict.get("response", "")
            task_states["llm"] = 'COMPLETED'
            logger.info("LLM task completed successfully")
        except Exception as e:
            logger.error(f"Error processing llm: {str(e)}")
            task_states["llm"] = 'FAILED'
        
    except Exception as e:
        logger.error(f"Error in test workflow: {str(e)}")
        return False
    
    logger.info(f"Test workflow completed with states: {task_states}")
    return True

if __name__ == "__main__":
    logger.info("Starting GAIA system...")
    
    # Wait for services to be ready
    wait_for_services()
    
    # Wait for RabbitMQ and declare queues
    wait_for_rabbitmq()
    
    # Initialize the database
    init_db()
    logger.info("Database initialized")
    
    # Start the monitoring thread
    monitor_thread = threading.Thread(target=monitor_and_scale, daemon=True)
    monitor_thread.start()
    logger.info("Monitoring thread started")
    
    # Run the test
    success = run_test()
    logger.info(f"Test workflow completed with success={success}")