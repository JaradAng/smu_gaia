import json
import random
import os
from celery import Celery

# Celery configuration
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
app = Celery('prompt_generator', broker=RABBITMQ_URL, backend='rpc://')

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def save_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def generate_zero_shot_prompt(query, text, triples):
    prompt = f"Based on the following data:\n{text}\n{triples}\nWhat is {query}"
    return prompt

def generate_tag_based_prompt(query, text, triples):
    tags = ["<instruction>", "<context>", "<input>", "<output>"]
    selected_tags = random.sample(tags, 3)  # Randomly select 3 tags
    
    prompt = f"{selected_tags[0]} Answer the following question based on the provided information.\n"
    prompt += f"{selected_tags[1]} Text: {text}\nKnowledge Graph: {triples}\n"
    prompt += f"{selected_tags[2]} {query}"
    
    return prompt

def generate_reasoning_prompt(query, text, triples):
    prompt = "<instruction> Answer the following question based on the provided information.\n"
    prompt += f"<context> Text: {text}\nKnowledge Graph: {triples}\n"
    prompt += f"<input> {query}\n"
    prompt += "<reasoning> Explain your thought process step by step.\n"
    prompt += "<thinking> Break down the problem and analyze it systematically."
    
    return prompt

@app.task(name='generate_prompts')
def generate_prompts(input_file_path):
    # Load the JSON file
    data = load_json(input_file_path)
    
    query = data['query']
    text = data['text']
    triples = data['knowledge_graph']
    
    # Generate prompts
    prompts = {
        "zero_shot": generate_zero_shot_prompt(query, text, triples),
        "tag_based": generate_tag_based_prompt(query, text, triples),
        "reasoning": generate_reasoning_prompt(query, text, triples)
    }
    
    # Prepare output data
    output_data = {
        "input": data,
        "prompts": prompts
    }
    
    # Save output to a new JSON file
    output_file_path = input_file_path.replace('.json', '_output.json')
    save_json(output_data, output_file_path)
    
    # Trigger the LLM agent task
    trigger_llm_agent.delay(output_file_path)
    
    return output_file_path

@app.task(name='trigger_llm_agent')
def trigger_llm_agent(output_file_path):
    # This is a placeholder for the LLM agent task
    # You would implement the actual LLM processing here
    print(f"LLM agent triggered with file: {output_file_path}")
    # Process the file with your LLM logic
    # ...

if __name__ == '__main__':
    app.start()
