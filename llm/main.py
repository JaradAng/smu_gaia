from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json
from legal_llm_analysis import process_legal_query
from transformers import AutoTokenizer, AutoModelForQuestionAnswering


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)


def perform_analysis(text, queries, model_name):
    """
    Perform analysis on the given text and queries using process_query.
    Returns a list of formatted responses.
    """
    responses = []
    for query in queries:
        # Use process_query to get the analysis results
        analysis_result = process_query(text, query, model_name)
        
        # Extract the necessary information from the analysis result
        answer = analysis_result["response"]["raw_text"]
        response_time = analysis_result["performance_metrics"]["response_time"]
        token_count = analysis_result["performance_metrics"]["token_count"]

        # Append the answer and metrics to the responses
        responses.append(f"Answer: {answer}, Response Time: {response_time}s, Token Count: {token_count}")
    
    return responses


@app.task(name="llm")
def llm_task(data):
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])
        model_name = data_dict.get("llm", "bert-base-uncased")

        if text and queries:
            responses = perform_analysis(text, queries, model_name)
        else:
            # If no text/queries, just return dummy response
            responses = [f"No inference needed for query: {q}" for q in queries]

        result = {"llm": model_name, "llmResult": " | ".join(responses)}

        return json.dumps(result)

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
