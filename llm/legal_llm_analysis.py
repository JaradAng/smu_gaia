import time
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import json
import psutil
import os

# Load the model and tokenizer from Hugging Face
model_name = "nlpaueb/legal-bert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForQuestionAnswering.from_pretrained(model_name)

def run_legal_llm_analysis(question):
    # Tokenize input (just the question in this case)
    inputs = tokenizer(question, return_tensors="pt", truncation=True)
    start_time = time.time()

    # Perform inference with the model
    outputs = model(**inputs)
    end_time = time.time()

    # Calculate response time
    response_time = end_time - start_time

    # Extract answer from the model's output
    answer_start = outputs.start_logits.argmax()
    answer_end = outputs.end_logits.argmax() + 1
    answer = tokenizer.convert_tokens_to_string(
        tokenizer.convert_ids_to_tokens(inputs['input_ids'][0][answer_start:answer_end])
    )

    # Gather token usage and system resource usage
    token_count = len(inputs['input_ids'][0])
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent

    # Assemble the output JSON
    output_json = {
        "test_id": "LEGAL_LLM_TEST_001",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "model_info": {
            "model_name": model_name,
            "model_version": "v1.0",
            "provider": "Hugging Face"
        },
        "input_processing": {
            "question_text": question,
            "token_count": token_count
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
        },
        "metadata": {
            "environment": "test",
            "tags": ["legal", "labor law", "remote work"]
        }
    }

    # Save the output to a JSON file
    json_file_name = "Legal_LLM_Analysis_Output.json"
    with open(json_file_name, 'w') as json_file:
        json.dump(output_json, json_file, indent=4)

    print(f"Response: {answer}")
    print(f"Response time: {response_time} seconds")
    print(f"Token usage: {token_count}")

    return output_json
