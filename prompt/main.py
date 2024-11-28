from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json
from prompt_generator import (
    generate_zero_shot_prompt,
    generate_tag_based_prompt,
    generate_reasoning_prompt,
    ProjectData
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)

@app.task(name="prompt")
def prompt_task(data):
    """
    Task for enhancing prompts.
    Generates three types of prompts based on the input data.
    """
    logger.info(f"Prompt received: {data}")
    
    try:
        project_data = ProjectData.from_json(data)
        
        project_data.prompts.zeroShot = generate_zero_shot_prompt(project_data)
        project_data.prompts.tagBased = generate_tag_based_prompt(project_data)
        project_data.prompts.reasoning = generate_reasoning_prompt(project_data)
        
        enhanced_prompt = project_data.to_json()
        logger.info(f"Prompts generated successfully")
        return enhanced_prompt
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
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