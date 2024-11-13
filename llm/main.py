from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json
from legal_llm_analysis import process_legal_query


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
    Task for LLM processing.
    Expects a JSON string containing textData and queries.
    """
    logger.info(f"LLM received: {data}")
    
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])
        
        # Process each query using the legal LLM
        responses = []
        for query in queries:
            response = f"Processed response for query: {query}"
            responses.append(response)
        #     result = process_legal_query(context=text, question=query)
        #     responses.append(result["response"]["raw_text"])
        
        result = {
            "llm": "gpt-4",  # or whatever LLM is being used
            "llmResult": " | ".join(responses)
            # "llm": "legal-bert",
            # "llmResult": " | ".join(responses),
            # "metrics": {
            #     "response_times": [result["performance_metrics"]["response_time"]],
            #     "token_counts": [result["performance_metrics"]["token_count"]],
            #     "cpu_usage": result["resource_usage"]["cpu_usage_percent"],
            #     "memory_usage": result["resource_usage"]["memory_usage_percent"]
            # }
        }
        
        logger.info(f"LLM produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error in LLM processing: {str(e)}")
        return json.dumps({"error": f"Error in LLM processing: {str(e)}"})


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
