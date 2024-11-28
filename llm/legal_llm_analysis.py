import time
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import json
import psutil
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "nlpaueb/legal-bert-base-uncased"
tokenizer = None
model = None

def initialize_model():
    """Initialize the model and tokenizer once"""
    global tokenizer, model
    if tokenizer is None or model is None:
        try:
            logger.info(f"Initializing model {MODEL_NAME}")
            
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            model = AutoModelForQuestionAnswering.from_pretrained(MODEL_NAME)
            
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

def process_legal_query(context, question):
    """
    Process a legal query using the legal-bert model.
    Returns a dictionary containing the analysis results.
    """
    global tokenizer, model
    
    if not initialize_model():
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
            "test_id": "LEGAL_LLM_TEST_001",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "model_info": {
                "model_name": MODEL_NAME,
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