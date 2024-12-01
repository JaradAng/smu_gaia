import time
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import json
import psutil
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "nlpaueb/legal-bert-base-uncased"
MODEL_PATH = os.environ.get('MODEL_PATH', '/app/models')
tokenizer = None
model = None

def initialize_model(model_name):
    """Initialize the model and tokenizer for a given model name"""
    global tokenizer, model
    if tokenizer is None or model is None or model_name != MODEL_NAME:
        try:
            logger.info(f"Initializing model {model_name}")
            
            # Create model directory if it doesn't exist
            model_dir = Path(MODEL_PATH) / model_name.split('/')[-1]
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if model exists locally
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
            
            if torch.cuda.is_available():
                model = model.cuda()
                logger.info("Model moved to GPU")
            else:
                logger.info("Running on CPU")
                
            logger.info("Model initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing model: {str(e)}")
            return False
    return True

def process_query(context, question, model_name=MODEL_NAME):
    """
    Process a query using the specified model.
    Returns a dictionary containing the analysis results.
    """
    global tokenizer, model
    
    if not initialize_model(model_name):
        error_msg = "Failed to initialize model"
        logger.error(error_msg)
        raise Exception(error_msg)

    try:
        inputs = tokenizer(question, context, return_tensors="pt", truncation=True)
        
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        start_time = time.time()
        with torch.no_grad():
            outputs = model(**inputs)
        end_time = time.time()
        response_time = end_time - start_time

        answer_start = outputs.start_logits.argmax()
        answer_end = outputs.end_logits.argmax() + 1
        answer = tokenizer.convert_tokens_to_string(
            tokenizer.convert_ids_to_tokens(inputs['input_ids'][0][answer_start:answer_end])
        )

        token_count = len(inputs['input_ids'][0])
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent

        return {
            "test_id": "LLM_TEST_001",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "model_info": {
                "model_name": model_name,
                "model_version": "v1.0",
                "provider": "Hugging Face"
            },
            "response": {
                "raw_text": answer,
                "detected_language": "en"
            },
            "performance_metrics": {
                "response_time": response_time,
                "token_count": token_count
            },
            "resource_usage": {
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise
