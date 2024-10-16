from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)


@app.task(name="llm")
def llm_task(data):
    """
    Task for processing data using a Language Learning Model (LLM).
    Simulates generating a response based on input data.
    """
    logger.info(f"LLM received: {data}")

    # Simulated for testing
    result = f"LLM generated response for: {data}"

    logger.info(f"LLM produced: {result}")
    return result


def send_llm_task(data):
    """
    Helper function to send the LLM task to Celery.
    """
    result = llm_task.delay(data)  # Send task asynchronously
    return result.get()  # Wait for the result and return it


def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for LLM.")
    worker = celery_worker.worker(app=app)  # Create worker instance
    options = {
        "loglevel": "INFO",
        "traceback": True,
    }

    worker.run(**options)


if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()
