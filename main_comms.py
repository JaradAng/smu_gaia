from celery import Celery
from kombu import Exchange, Queue
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Celery app with RabbitMQ as the broker
app = Celery(
    "gaia_master",
    broker=os.getenv("CELERY_BROKER_URL", "pyamqp://guest@localhost//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "rpc://"),
)  # Backend for task result handling

# Define task and result exchanges
task_exchange = Exchange("tasks", type="direct")
result_exchange = Exchange("results", type="direct")

# Set up the queues for the tools GAIA will communicate with
app.conf.task_queues = (
    Queue("chunker", task_exchange, routing_key="chunker"),
    Queue("embedding", task_exchange, routing_key="embedding"),
    Queue("database", task_exchange, routing_key="database"),
    Queue("ner", task_exchange, routing_key="ner"),
    Queue("llm", task_exchange, routing_key="llm"),
    Queue("results", result_exchange, routing_key="results"),  # Queue for results
)

# Routing tasks to appropriate queues
app.conf.task_routes = {
    "chunker_task": {"queue": "chunker", "routing_key": "chunker"},
    "embedding_task": {"queue": "embedding", "routing_key": "embedding"},
    "database_task": {"queue": "database", "routing_key": "database"},
    "ner_task": {"queue": "ner", "routing_key": "ner"},
    "llm_task": {"queue": "llm", "routing_key": "llm"},
}

# Celery worker configuration for concurrency and task execution
app.conf.worker_concurrency = 4
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
app.conf.task_soft_time_limit = 300
app.conf.task_time_limit = 360
app.conf.task_retry = True
app.conf.task_default_retry_delay = 30
app.conf.task_max_retries = 5

# minimal task set up. loogic will be handled seperately either in GAIA or the external tool


@app.task(name="chunker_task")
def chunker_task(document):
    """Task for interacting with the chunker tool."""
    logger.info(f"Chunking document: {document}")
    # add comm
    return f"Chunked document: {document}"


@app.task(name="embedding_task")
def embedding_task(chunked_document):
    """Task for interacting with the embedding tool."""
    logger.info(f"Embedding document: {chunked_document}")
    # Minimal communication logic; processing handled by external tool
    return f"Embedding completed for: {chunked_document}"


@app.task(name="database_task")
def database_task(embedded_document):
    """Task for interacting with the database tool."""
    logger.info(f"Storing document in database: {embedded_document}")
    # Minimal communication logic; database storage handled externally
    return f"Stored in database: {embedded_document}"


@app.task(name="ner_task")
def ner_task(document):
    """Task for interacting with the NER tool."""
    logger.info(f"Performing NER on document: {document}")
    # Minimal communication logic; NER handled by external tool
    return f"NER completed for: {document}"


@app.task(name="llm_task")
def llm_task(document):
    """Task for interacting with the Large Language Model (LLM)."""
    logger.info(f"Processing with LLM on document: {document}")
    # Minimal communication logic; LLM processing done externally
    return f"LLM result for: {document}"


@app.task(name="quality_control")
def quality_control(task_result, task_name):
    """Quality control task to verify the result of a task."""
    logger.info(f"Performing quality control on {task_name} result: {task_result}")
    # Perform a simple quality control check (this could be more complex depending on GAIA)
    return f"QC Passed: {task_name}"


@app.task(bind=True, name="error_handler")
def error_handler(self, task_id, exception):
    """Handle errors encountered by any task."""
    logger.error(f"Task {task_id} failed with error: {str(exception)}")
    # Retry logic in case of failure
    self.retry(exc=exception, countdown=60, max_retries=3)


# Main entry point for starting Celery workers
if __name__ == "__main__":
    app.start()