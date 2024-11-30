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


# Definetask
@app.task(name="vector_db")
def vector_db_task(data):
    """
    Task for Vector DB operations.
    Expects a JSON string containing textData, embedding, and vectorDB information.
    """
    logger.info(f"Vector DB received: {data}")
    
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        embedding = data_dict.get("embedding", "")
        vector_db = data_dict.get("vectorDB", "")
        
        # Simulated vector DB processing (replace with actual vector DB logic)
        # Here you would typically:
        # 1. Create embeddings for the text
        # 2. Store them in the vector DB
        # 3. Create similarity indices
        
        result = {
            "loaded": True,
            "vectorDB": vector_db,
            "embedding": embedding,
            "similarityIndices": {
                "method": "cosine",
                "dimensions": 768
            }
        }
        
        logger.info(f"Vector DB produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error in Vector DB processing: {str(e)}")
        return json.dumps({"error": f"Error in Vector DB processing: {str(e)}"})


def send_vector_db_task(data):
    """
    Helper function to send the vector DB task to Celery.
    """
    result = vector_db_task.delay(data)
    return result.get()


def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for vector DB.")
    worker = celery_worker.worker(app=app)
    options = {
        "loglevel": "INFO",
        "traceback": True,
    }

    worker.run(**options)


if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()
