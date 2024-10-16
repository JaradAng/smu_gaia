from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os

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
    Task for processing data in the graph database.
    Simulates a process to create or update a graph for the given data.
    """
    logger.info(f"Graph DB received: {data}")

    # Simulate for test
    result = f"Graph created for: {data}"

    logger.info(f"Graph DB produced: {result}")
    return result


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
