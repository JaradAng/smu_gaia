from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json
from prompt_generator import (
    generate_zero_shot_prompt,
    generate_tag_based_prompt,
    generate_reasoning_prompt,
    ProjectData,
    KnowledgeGraph,
    Prompts
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)

@app.task(name="prompt")
def prompt_task(data, wait_for_kg=False, wait_for_prompts=False):
    """
    Task for enhancing prompts.
    Generates three types of prompts based on the input data.
    """
    logger.info(f"Prompt received: {data}")
    
    try:
        # Parse the input data into a ProjectData object
        if isinstance(data, str):
            data = json.loads(data)
            
        project_data = ProjectData(
            domain=data.get("domain", "default"),
            docsSource=data.get("docsSource", "/shared_data"),
            queries=data.get("queries", []),
            id=data.get("id", "default"),
            kg=KnowledgeGraph(
                kgTriples=[],
                ner=[]
            )
        )
        
        # Use the additional arguments as needed
        if wait_for_kg:
            logger.info("Waiting for Knowledge Graph completion.")
        if wait_for_prompts:
            logger.info("Waiting for Prompts completion.")
        
        # Generate prompts
        zero_shot = generate_zero_shot_prompt(project_data)
        tag_based = generate_tag_based_prompt(project_data)
        reasoning = generate_reasoning_prompt(project_data)
        
        # Return the results in a structured format
        result = {
            "prompts": {
                "zeroShot": zero_shot,
                "tagBased": tag_based,
                "reasoning": reasoning,
                "custom": None
            }
        }
        
        logger.info(f"Prompts generated successfully")
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error in prompt processing: {str(e)}")
        return json.dumps({"error": f"Error in prompt processing: {str(e)}"})

def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for prompt processing.")
    worker = celery_worker.worker(app=app)
    options = {
        "loglevel": "INFO",
        "traceback": True,
    }
    worker.run(**options)

if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()