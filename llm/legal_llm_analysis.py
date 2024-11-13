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

# Define a legal domain context and question
context = """
Under U.S. labor law, employees have certain rights when it comes to remote work policies. 
Employers are required to ensure that their remote work policies comply with all applicable regulations, 
including wage and hour laws, occupational health and safety standards, and anti-discrimination statutes.
"""
question = "What are the legal obligations of employers regarding remote work policies?"

# Tokenize input (context and question)
inputs = tokenizer(question, context, return_tensors="pt", truncation=True)

# Start timing the LLM query
start_time = time.time()

# Perform inference with the model
outputs = model(**inputs)

# Timing ends
end_time = time.time()
response_time = end_time - start_time

# Extracting answer from the model's output
answer_start = outputs.start_logits.argmax()
answer_end = outputs.end_logits.argmax() + 1
answer = tokenizer.convert_tokens_to_string(tokenizer.convert_ids_to_tokens(inputs['input_ids'][0][answer_start:answer_end]))

# Extracting token usage
token_count = len(inputs['input_ids'][0])

# Gathering system resource usage
cpu_usage = psutil.cpu_percent(interval=1)
memory_usage = psutil.virtual_memory().percent

# Assembling the JSON output for database storage
output_json = {
    "test_id": "LEGAL_LLM_TEST_001",
    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
    "model_info": {
        "model_name": model_name,
        "model_version": "v1.0",
        "provider": "Hugging Face"
    },
    "input_processing": {
        "context_text": context,
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

# Save the output to a JSON file for database storage
json_file_name = "Legal_LLM_Analysis_Output.json"
with open(json_file_name, 'w') as json_file:
    json.dump(output_json, json_file, indent=4)

# Print the output for debugging or logging
print(f"Response: {answer}")
print(f"Response time: {response_time} seconds")
print(f"Token usage: {token_count}")
