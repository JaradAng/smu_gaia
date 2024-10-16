from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os

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
    Simulates chunking a document into parts (chunks).
    """
    logger.info(f"Chunker received: {data}")

    # Simulated for testing
    chunks = [f"Chunk {i}" for i in range(1, 4)]

    logger.info(f"Chunker produced: {chunks}")
    return chunks


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
