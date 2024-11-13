import time
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import json
import psutil
import os

def process_legal_query(context, question):
    """
    Process a legal query using the legal-bert model.
    Returns a dictionary containing the analysis results.
    """
    # Load the model and tokenizer from Hugging Face
    model_name = "nlpaueb/legal-bert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForQuestionAnswering.from_pretrained(model_name)

    # Tokenize input
    inputs = tokenizer(question, context, return_tensors="pt", truncation=True)

    # Start timing the LLM query
    start_time = time.time()
    outputs = model(**inputs)
    end_time = time.time()
    response_time = end_time - start_time

    # Extract answer
    answer_start = outputs.start_logits.argmax()
    answer_end = outputs.end_logits.argmax() + 1
    answer = tokenizer.convert_tokens_to_string(
        tokenizer.convert_ids_to_tokens(inputs['input_ids'][0][answer_start:answer_end])
    )

    # Gather metrics
    token_count = len(inputs['input_ids'][0])
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent

    return {
        "test_id": "LEGAL_LLM_TEST_001",
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
