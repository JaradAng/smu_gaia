from kombu import Connection, Queue
from celery import Celery
import os

app = Celery('gaia', broker=os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//'))

def get_queue_length(queue_name):
    with Connection(app.conf.broker_url) as conn:
        channel = conn.channel()
        queue = Queue(queue_name, channel=channel)
        queue_state = queue.queue_declare(passive=True)
        message_count = queue_state.message_count
        return message_count