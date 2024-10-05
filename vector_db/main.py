from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Celery('gaia', broker=os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//'))

# Definetask
@app.task(name='vector_db_task')
def vector_db_task(data):
    """
    Task for processing and storing vectors in the database.
    Simulates storing vectors related to the input data.
    """
    logger.info(f"Vector DB received: {data}")
    
    # Simulate for test
    result = f"Vectors stored for: {data}"
    
    logger.info(f"Vector DB produced: {result}")
    return result

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


if __name__ == '__main__':
    logger.info("Starting Celery app.")
    app.start()
