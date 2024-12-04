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

# Industry-specific or default model
MODEL_NAME = "nlpaueb/legal-bert-base-uncased"
MODEL_PATH = os.environ.get('MODEL_PATH', '/app/models')

# Supporting models
SUPPORTING_MODELS = [
    {
        "name": "distilbert-base-uncased-distilled-squad",
        # Small supporting model
        "size": "small"
    },
    {
        "name": "bert-base-uncased",  # Medium supporting model
        "size": "medium"
    },
    {
        "name": "bert-large-uncased-whole-word-masking-finetuned-squad",
        # Large supporting model
        "size": "large"
    }
]

# Example prompt structure
prompts = {
    "zeroShot": "What are the legal risks?",
    "reasoning": "Explain the implications step by step.",
    "tagBased": "Summarize the document with legal tags.",
    "custom": ["Summarize this document.", "Extract key dates."]
}


# Initialize a model and tokenizer for a specific model
def initialize_model(model_name, size=None):
    """
    Initialize the tokenizer and model for a specific model.
    If size is provided, it's for supporting models; otherwise, it uses the default model.
    """
    try:
        size_path = size if size else model_name.split('/')[-1]
        logger.info(
            f"Initializing model {model_name} ({'default' if not size else size})...")
        model_dir = Path(MODEL_PATH) / size_path
        model_dir.mkdir(parents=True, exist_ok=True)

        # Check if the model exists locally
        if (model_dir / 'config.json').exists():
            logger.info(f"Loading model from local path: {model_dir}")
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            model = AutoModelForQuestionAnswering.from_pretrained(
                str(model_dir))
        else:
            logger.info(
                f"Downloading {model_name} ({'default' if not size else size}) from Hugging Face")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForQuestionAnswering.from_pretrained(
                model_name)

            # Save the model locally
            logger.info(f"Saving model to {model_dir}")
            tokenizer.save_pretrained(str(model_dir))
            model.save_pretrained(str(model_dir))

        if torch.cuda.is_available():
            model = model.cuda()
            logger.info("Model moved to GPU")
        else:
            logger.info("Running on CPU")

        return tokenizer, model
    except Exception as e:
        logger.error(f"Error initializing model {model_name}: {str(e)}")
        raise


# Perform inference with the model
def run_inference(tokenizer, model, question):
    """
    Run inference on a single question and return the result.
    """
    inputs = tokenizer(question, return_tensors="pt", truncation=True)
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    start_time = time.time()
    with torch.no_grad():
        outputs = model(**inputs)
    end_time = time.time()

    # Extract the answer
    answer_start = outputs.start_logits.argmax()
    answer_end = outputs.end_logits.argmax() + 1
    answer = tokenizer.convert_tokens_to_string(
        tokenizer.convert_ids_to_tokens(
            inputs['input_ids'][0][answer_start:answer_end])
    )

    response_time = end_time - start_time
    logger.info(
        f"Response: {answer} (Response time: {response_time:.2f} seconds)")
    return {
        "answer": answer,
        "response_time": response_time
    }


# Process prompts for a given model
def process_prompts_with_model(tokenizer, model, model_name):
    """
    Process all prompts using a given model.
    Returns results for each prompt type.
    """
    results = {}
    for prompt_type, prompt in prompts.items():
        if not prompt:  # Skip if the prompt is empty or missing
            logger.info(
                f"No prompt provided for {prompt_type}. Skipping...")
            continue

        logger.info(
            f"Processing {prompt_type} prompt with {model_name} model...")

        if prompt_type == "custom":
            custom_results = []
            for custom_prompt in prompt:
                result = run_inference(tokenizer, model, custom_prompt)
                custom_results.append(
                    {"prompt": custom_prompt, "response": result})
            results["custom"] = custom_results
        else:
            result = run_inference(tokenizer, model, prompt)
            results[prompt_type] = {"prompt": prompt,
                                    "response": result}

    return results


# Main function to process models and prompts
def process_all_models_and_prompts():
    """
    Process the industry-specific model first, then supporting models.
    """
    final_results = {}

    # Step 1: Process the industry-specific (default) model
    try:
        logger.info(f"Processing industry-specific model: {MODEL_NAME}")
        tokenizer, model = initialize_model(
            MODEL_NAME)  # No size for the default model
        industry_results = process_prompts_with_model(tokenizer, model,
                                                      "industry-specific")
        final_results["industry-specific"] = industry_results
    except Exception as e:
        logger.error(
            f"Failed to process industry-specific model: {str(e)}")

    # Step 2: Process supporting models
    for supporting_model in SUPPORTING_MODELS:
        model_name = supporting_model["name"]
        model_size = supporting_model["size"]

        try:
            logger.info(
                f"Processing supporting model: {model_name} ({model_size})")
            tokenizer, model = initialize_model(model_name, model_size)
            supporting_results = process_prompts_with_model(tokenizer,
                                                            model,
                                                            model_size)
            final_results[model_size] = supporting_results
        except Exception as e:
            logger.error(
                f"Failed to process supporting model ({model_name}): {str(e)}")

    # Save the aggregated results to a JSON file
    with open("LLM_Multi_Model_Prompt_Results.json", "w") as json_file:
        json.dump(final_results, json_file, indent=4)

    logger.info("Processing completed for all models and prompts.")
    return final_results


# Run the program
if __name__ == "__main__":
    results = process_all_models_and_prompts()
