from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)


@app.task(name="prompt")
def prompt_task(data):
    """
    Task for enhancing a prompt.
    Simulates processing a prompt and returning an enhanced version.
    """
    logger.info(f"Prompt received: {data}")

    enhanced_prompt = f"Enhanced prompt: {data}"

    logger.info(f"Prompt produced: {enhanced_prompt}")
    return enhanced_prompt


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
