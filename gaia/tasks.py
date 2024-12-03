# tasks.py

from celery import Celery
from kombu import Queue
from container_manager import ContainerManager
import os
import time
import logging

app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend="db+sqlite:///data/results.sqlite",
)

# Setup routing keys and ensure queues are declared
app.conf.task_queues = (
    Queue("chunker", routing_key="chunker", durable=True),
    Queue("vector_db", routing_key="vector_db", durable=True),
    Queue("graph_db", routing_key="graph_db", durable=True),
    Queue("llm", routing_key="llm", durable=True),
    Queue("prompt", routing_key="prompt", durable=True),
)

# Define task names for each queue
TASK_NAMES = {
    "chunker": "chunker",
    "vector_db": "vector_db",
    "graph_db": "graph_db",
    "llm": "llm",
    "prompt": "prompt",
}

# Configure task settings
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes timeout
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_heartbeat=60,
    broker_pool_limit=10,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_transport_options={
        'confirm_publish': True,
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    }
)

# Configure task routes
app.conf.task_routes = {
    'chunker': {'queue': 'chunker'},
    'graph_db': {'queue': 'graph_db'},
    'llm': {'queue': 'llm'},
    'prompt': {'queue': 'prompt'}
}

logger = logging.getLogger(__name__)

@app.task(name="chunker", bind=True, max_retries=3)
def chunker_task(self, input_data):
    logger.info(f"Starting task {self.request.id}")
    manager = ContainerManager()
    container = manager.start_container(
        image_name=os.environ.get("chunker"),
        env_vars={"INPUT_DATA": input_data},
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
        logger.info(f"Task {self.request.id} completed successfully")
        return result
    except Exception as exc:
        logger.error(f"Task {self.request.id} failed: {exc}")
        raise
    finally:
        manager.stop_container(container)

@app.task(name="vector_db", bind=True, max_retries=3)
def vector_db_task(self, input_data):
    manager = ContainerManager()
    container = manager.start_container(
        image_name=os.environ.get("vector_db"),
        env_vars={"INPUT_DATA": input_data},
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    except Exception as exc:
        self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        manager.stop_container(container)
    return result

@app.task(name="graph_db", bind=True, max_retries=3)
def graph_db_task(self, input_data):
    logger.info(f"Starting task {self.request.id}")
    manager = ContainerManager()
    container = manager.start_container(
        image_name=os.environ.get("graph_db"),
        env_vars={"INPUT_DATA": input_data},
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
        logger.info(f"Task {self.request.id} completed successfully")
        return result
    except Exception as exc:
        logger.error(f"Task {self.request.id} failed: {exc}")
        raise
    finally:
        manager.stop_container(container)

@app.task(name="llm", bind=True, max_retries=3)
def llm_task(self, input_data):
    manager = ContainerManager()
    image_name = os.environ.get('DOCKER_IMAGE_LLM', 'llm')
    container = manager.start_container(
        image_name=image_name,
        env_vars={'INPUT_DATA': input_data}
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    except Exception as exc:
        self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        manager.stop_container(container)
    return result

@app.task(name="prompt", bind=True, max_retries=3)
def prompt_task(self, input_data, wait_for_kg=False, wait_for_prompts=False):
    manager = ContainerManager()
    env_vars = {
        "INPUT_DATA": input_data,
        "WAIT_FOR_KG": str(wait_for_kg).lower(),
        "WAIT_FOR_PROMPTS": str(wait_for_prompts).lower()
    }
    
    container = manager.start_container(
        image_name=os.environ.get("prompt"),
        env_vars=env_vars,
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    except Exception as exc:
        self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        manager.stop_container(container)
    return result

def wait_for_rabbitmq():
    """Wait for RabbitMQ to be ready and ensure queues are declared."""
    print("Waiting for RabbitMQ...")
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            with app.connection_for_write() as conn:
                conn.ensure_connection(max_retries=3)
                channel = conn.channel()
                for queue_name in TASK_NAMES.keys():
                    queue = Queue(
                        queue_name,
                        channel=channel,
                        durable=True,
                        auto_delete=False,
                        arguments={'x-queue-type': 'classic'}
                    )
                    queue.declare()
                    print(f"Declared queue: {queue_name}")
            print("RabbitMQ is ready!")
            return True
        except Exception as e:
            print(f"Waiting for RabbitMQ... Attempt {i+1}/{max_retries}. Error: {str(e)}")
            if i == max_retries - 1:
                print("Detailed connection error:", str(e))
            time.sleep(retry_interval)
    
    raise Exception("RabbitMQ connection failed after maximum retries")