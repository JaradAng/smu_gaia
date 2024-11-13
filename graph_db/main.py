from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)


@app.task(name="graph_db")
def graph_db_task(data):
    """
    Task for Graph DB operations.
    Expects a JSON string containing textData and queries.
    """
    logger.info(f"Graph DB received: {data}")
    
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])
        
        # Simulated knowledge graph processing (replace with actual KG logic)
        # Here you would typically:
        # 1. Extract entities and relationships
        # 2. Create knowledge graph triples
        # 3. Store in graph database
        
        result = {
            "kgTriples": [
                "entity1 - relation1 - entity2",
                "entity2 - relation2 - entity3",
                "entity1 - relation3 - entity4",
                "entity3 - relation4 - entity5",
                "entity4 - relation5 - entity5"
            ],
            "ner": ["spacy", "nltk"],  # List of NER techniques used
        }
        
        logger.info(f"Graph DB produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error in Graph DB processing: {str(e)}")
        return json.dumps({"error": f"Error in Graph DB processing: {str(e)}"})


def send_graph_db_task(data):
    """
    Helper function to send the graph DB task to Celery.
    """
    result = graph_db_task.delay(data)  # Send task asynchronously
    return result.get()  # Wait for the result and return it


def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for graph DB.")
    worker = celery_worker.worker(app=app)  # Create worker instance
    options = {
        "loglevel": "INFO",
        "traceback": True,
    }

    worker.run(**options)


if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()
