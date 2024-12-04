import requests
import logging
import sys
import subprocess
import json
import os
from huggingface_hub import hf_hub_download

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_internet_connection():
    try:
        # Try to connect to Hugging Face
        response = requests.get("https://huggingface.co", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error checking internet connection: {str(e)}")
        return False

def check_dns_resolution():
    try:
        # Try to resolve huggingface.co using older subprocess syntax
        result = subprocess.Popen(['nslookup', 'huggingface.co'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()
        output = stdout.decode('utf-8')
        logger.info(f"DNS lookup result:\n{output}")
        return "huggingface.co" in output
    except Exception as e:
        logger.error(f"Error checking DNS resolution: {str(e)}")
        return False

def test_huggingface_api():
    try:
        # Try to get model info directly from the Hugging Face API
        model_id = "gpt2"
        api_url = f"https://huggingface.co/api/models/{model_id}"
        
        logger.info(f"Attempting to get model info from {api_url}")
        response = requests.get(api_url)
        
        if response.status_code == 200:
            model_info = response.json()
            logger.info(f"Successfully retrieved model info: {json.dumps(model_info, indent=2)}")
            return True
        else:
            logger.error(f"Failed to get model info. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error during API test: {str(e)}")
        return False

def test_model_file_download():
    try:
        # Try to download a small file from the model (config.json)
        model_id = "gpt2"
        file_name = "config.json"
        download_url = f"https://huggingface.co/{model_id}/resolve/main/{file_name}"
        
        logger.info(f"Attempting to download {file_name} from {download_url}")
        response = requests.get(download_url)
        
        if response.status_code == 200:
            # Save to a temporary file
            temp_file = f"/tmp/{file_name}"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            # Check if file was saved
            if os.path.exists(temp_file):
                file_size = os.path.getsize(temp_file)
                logger.info(f"Successfully downloaded {file_name} ({file_size} bytes)")
                
                # Read and log the content
                with open(temp_file, 'r') as f:
                    content = json.load(f)
                    logger.info(f"File content: {json.dumps(content, indent=2)}")
                
                return True
            else:
                logger.error(f"File was not saved to {temp_file}")
                return False
        else:
            logger.error(f"Failed to download file. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error during file download test: {str(e)}")
        return False

def test_huggingface_hub_download():
    try:
        # Try to download using huggingface_hub
        model_id = "gpt2"
        filename = "config.json"
        
        logger.info(f"Attempting to download {filename} using huggingface_hub...")
        
        # Create a cache directory with write permissions
        cache_dir = "/tmp/huggingface"
        os.makedirs(cache_dir, exist_ok=True)
        
        # Download the file
        downloaded_path = hf_hub_download(
            repo_id=model_id,
            filename=filename,
            cache_dir=cache_dir
        )
        
        logger.info(f"Successfully downloaded to: {downloaded_path}")
        
        # Read and verify the content
        with open(downloaded_path, 'r') as f:
            content = json.load(f)
            logger.info(f"File content: {json.dumps(content, indent=2)}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error during huggingface_hub download test: {str(e)}")
        return False

def main():
    # Check internet connection
    logger.info("Checking internet connection...")
    if not check_internet_connection():
        logger.error("Cannot connect to Hugging Face. Please check your internet connection.")
        sys.exit(1)

    # Check DNS resolution
    logger.info("Checking DNS resolution...")
    if not check_dns_resolution():
        logger.error("Cannot resolve huggingface.co. Please check your DNS settings.")
        sys.exit(1)

    # If we get here, basic connectivity is working
    logger.info("Basic connectivity checks passed!")

    # Test Hugging Face API
    logger.info("Testing Hugging Face API...")
    if test_huggingface_api():
        logger.info("Hugging Face API test passed!")
    else:
        logger.error("Hugging Face API test failed!")
        
    # Test model file download
    logger.info("Testing model file download...")
    if test_model_file_download():
        logger.info("Model file download test passed!")
    else:
        logger.error("Model file download test failed!")
        
    # Test huggingface_hub download
    logger.info("Testing huggingface_hub download...")
    if test_huggingface_hub_download():
        logger.info("huggingface_hub download test passed!")
    else:
        logger.error("huggingface_hub download test failed!")

if __name__ == "__main__":
    main()