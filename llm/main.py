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


@app.task(name="llm")
def llm_task(data):
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])
        model_name = data_dict.get("llm", "bert-base-uncased")
        
        # Only download the model if we're actually going to use it
        if text and queries:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForQuestionAnswering.from_pretrained(model_name)
            
            responses = []
            for query in queries:
                # Tokenize input
                inputs = tokenizer(query, text, return_tensors="pt", truncation=True, max_length=512)
                
                # Get model outputs
                outputs = model(**inputs)
                
                # Process outputs to get answer
                answer_start = outputs.start_logits.argmax()
                answer_end = outputs.end_logits.argmax()
                answer = tokenizer.decode(inputs["input_ids"][0][answer_start:answer_end+1])
                
                responses.append(answer)
        else:
            # If no text/queries, just return dummy response
            responses = [f"No inference needed for query: {q}" for q in queries]
        
        result = {
            "llm": model_name,
            "llmResult": " | ".join(responses)
        }
        
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
