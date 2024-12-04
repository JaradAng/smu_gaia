from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json
from legal_llm_analysis import process_legal_query
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import time
import torch
import psutil
from pathlib import Path
from test_model_download import (
    check_internet_connection,
    check_dns_resolution,
    test_huggingface_api,
    test_model_file_download  
)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)


@app.task(name="llm")
def llm_task(data, wait_for_prompts=False):
    """
    Process text using LLM.
    
    Args:
        data: Input data containing text and queries
        wait_for_prompts: Flag indicating whether to wait for prompts (optional)
    """
    try:
        if wait_for_prompts:
            logger.info("Waiting for prompts completion.")
        
        # Perform environment checks
        if not check_internet_connection():
            raise Exception("No internet connection.")
        if not check_dns_resolution():
            raise Exception("DNS resolution failed for huggingface.co.")
        if not test_huggingface_api():
            raise Exception("Failed to access Hugging Face API.")
        if not test_model_file_download():
            raise Exception("Failed to download test model file.")
        
        data_dict = json.loads(data) if isinstance(data, str) else data
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])
        model_name = data_dict.get("llm", "bert-base-uncased")
        
        # Initialize model and tokenizer
        model_dir = Path('/app/models') / model_name.split('/')[-1]
        model_dir.mkdir(parents=True, exist_ok=True)
        
        if (model_dir / 'config.json').exists():
            logger.info(f"Loading model from local path: {model_dir}")
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            model = AutoModelForQuestionAnswering.from_pretrained(str(model_dir))
        else:
            logger.info(f"Downloading model from Hugging Face")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForQuestionAnswering.from_pretrained(model_name)
            
            # Save model locally
            logger.info(f"Saving model to {model_dir}")
            tokenizer.save_pretrained(str(model_dir))
            model.save_pretrained(str(model_dir))
        
        if text and queries:
            responses = []
            for query in queries:
                # Tokenize input
                inputs = tokenizer(query, text, return_tensors="pt", truncation=True, max_length=512)
                
                # Measure performance metrics
                start_time = time.time()
                with torch.no_grad():
                    outputs = model(**inputs)
                end_time = time.time()
                response_time = end_time - start_time
                
                # Process outputs to get answer
                answer_start = outputs.start_logits.argmax()
                answer_end = outputs.end_logits.argmax()
                answer = tokenizer.decode(inputs["input_ids"][0][answer_start:answer_end+1])
                
                # Calculate token count
                token_count = len(inputs['input_ids'][0])
                
                # Measure resource usage
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.virtual_memory().percent
                
                # Append detailed response
                responses.append({
                    "query": query,
                    "answer": answer,
                    "performance_metrics": {
                        "response_time": response_time,
                        "token_count": token_count
                    },
                    "resource_usage": {
                        "cpu_usage_percent": cpu_usage,
                        "memory_usage_percent": memory_usage
                    }
                })
        else:
            responses = [{"query": q, "answer": f"No inference needed for query: {q}"} for q in queries]
        
        result = {
            "llm": model_name,
            "llmResult": responses
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