from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)


@app.task(name="chunker")
def chunker_task(data):
    """
    Task for chunking a document.
    Expects a JSON string containing textData and optional chunkingMethod.
    """
    logger.info(f"Chunker received: {data}")
    
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        method = data_dict.get("chunkingMethod", "paragraph")
        
        # Simulated chunking (replace with actual chunking logic)
        chunks = [text[i:i+100] for i in range(0, len(text), 100)]
        
        result = {
            "chunkingMethod": method,
            "chunks": chunks
        }
        
        logger.info(f"Chunker produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error processing chunks: {str(e)}")
        return json.dumps({"error": f"Error processing chunks: {str(e)}"})


def send_chunking_task(data):
    """
    Helper function to send the chunker task to Celery.
    """
    result = chunker_task.delay(data)  # Send task asynchronously
    return result.get()  # Wait for the result and return it


def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for chunker.")
    worker = celery_worker.worker(app=app)
    options = {
        "loglevel": "DEBUG",
        "traceback": True,
    }

    worker.run(**options)


# Entry point to start the Celery worker or use the app programmatically
if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()


#  from celery import Celery
# import os

# # Initialize Celery app
# app = Celery('gaia', broker=os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//'))

# @app.task(name='chunker_task')
# def chunker_task(data):
#     print(f"Chunker received: {data}")
#     # Simulate chunking process
#     chunks = [f"Chunk {i}" for i in range(1, 4)]
#     print(f"Chunker produced: {chunks}")
#     return chunks

# if __name__ == '__main__':
#     app.start()
