# tasks.py

from celery import Celery
from kombu import Queue
from container_manager import ContainerManager
import os

app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend="db+sqlite:///data/results.sqlite",
)

# Setup routing keys
app.conf.task_queues = (
    Queue("chunker", routing_key="chunker"),
    Queue("vector_db", routing_key="vector_db"),
    Queue("graph_db", routing_key="graph_db"),
    Queue("llm", routing_key="llm"),
    Queue("prompt", routing_key="prompt"),
)

# Define task names for each queue
TASK_NAMES = {
    "chunker": "chunker",
    "vector_db": "vector_db",
    "graph_db": "graph_db",
    "llm": "llm",
    "prompt": "prompt",
}


@app.task(name="chunker")
def chunker_task(input_data):
    manager = ContainerManager()
    container = manager.start_container(
        image_name=os.environ.get("chunker"),
        env_vars={"INPUT_DATA": input_data},
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    finally:
        manager.stop_container(container)
    return result


@app.task(name="vector_db")
def vector_db_task(input_data):
    manager = ContainerManager()
    container = manager.start_container(
        image_name=os.environ.get("vector_db"),
        env_vars={"INPUT_DATA": input_data},
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    finally:
        manager.stop_container(container)
    return result


@app.task(name="graph_db")
def graph_db_task(input_data):
    manager = ContainerManager()
    container = manager.start_container(
        image_name=os.environ.get("graph_db"),
        env_vars={"INPUT_DATA": input_data},
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    finally:
        manager.stop_container(container)
    return result


@app.task(name="llm")
def llm_task(input_data):
    manager = ContainerManager()
    image_name = os.environ.get('DOCKER_IMAGE_LLM', 'llm')
    container = manager.start_container(
        image_name=image_name,
        env_vars={'INPUT_DATA': input_data}
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    finally:
        manager.stop_container(container)
    return result


@app.task(name="prompt")
def prompt_task(input_data):
    manager = ContainerManager()
    container = manager.start_container(
        image_name=os.environ.get("prompt"),
        env_vars={"INPUT_DATA": input_data},
        command=["python", "main.py"],
    )
    try:
        container.wait()
        result = manager.get_logs(container)
    finally:
        manager.stop_container(container)
    return result
