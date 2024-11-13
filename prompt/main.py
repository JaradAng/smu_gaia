from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)


@app.task(name="prompt")
def prompt_task(data):
    """
    Task for Prompt processing.
    Expects a JSON string containing textData, queries, and knowledge graph information.
    """
    logger.info(f"Prompt received: {data}")
    
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])
        kg_data = data_dict.get("kg", {})
        
        # Get KG triples if available
        kg_triples = kg_data.get("kgTriples", []) if kg_data else []
        
        # Simulated prompt processing (replace with actual prompt logic)
        # Here you would typically:
        # 1. Generate prompts using the text, queries, and KG triples
        # 2. Format them according to the LLM requirements
        
        result = {
            "generatedPrompts": [
                f"Generated prompt using KG triples: {', '.join(kg_triples[:2])}",
                f"Context: {text[:100]}...",
                f"Query: {queries[0] if queries else 'No query provided'}"
            ],
            "ragText": "Generated RAG text based on knowledge graph and queries"
        }
        
        logger.info(f"Prompt produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error in Prompt processing: {str(e)}")
        return json.dumps({"error": f"Error in Prompt processing: {str(e)}"})


def send_prompt_task(data):
    """
    Helper function to send the prompt task to Celery.
    """
    result = prompt_task.delay(data)
    return result.get()


def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for prompt task.")
    worker = celery_worker.worker(app=app)
    options = {
        "loglevel": "INFO",
        "traceback": True,
    }

    worker.run(**options)


if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()
