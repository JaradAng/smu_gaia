import json
from celery import Celery
from celery.bin import worker as celery_worker
import nltk
from nltk import word_tokenize, pos_tag
from nltk.chunk import RegexpParser
import logging
import os
from sentence_transformers import SentenceTransformer
import numpy as np

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

# Download required NLTK data
nltk.download('punkt')
nltk.download('punkt_tab') 
nltk.download('averaged_perceptron_tagger_eng')  # For POS tagging
print('NLTK packages downloaded!')

def load_files(directory):
    """
    Loads in text files in specified directory.
    :param directory: Directory holding files
    :return: List of text from each file
    """
    texts = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            with open(os.path.join(directory, filename), 'r',
                      encoding='utf-8') as file:
                texts.append(file.read())
    print('Text loaded!')
    return texts


def embed_chunks(chunks):
    """
    Embeds the chunks using a SentenceTransformer model.
    :param chunks: Chunked text that is to be embedded
    :return: List of lists (converted from numpy arrays)
    """
    # Load pre-trained Sentence-BERT model
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    # Generate embeddings for each chunk
    embeddings = model.encode(chunks)
    
    # Convert numpy arrays to lists before returning
    return embeddings.tolist()  # Convert to Python list


def fixed_size_chunking(text, chunk_size=512):
    """
    Performs fixed-sized chunking on the text.
    :param text: Text that is to be chunked
    :param chunk_size: The fixed chunking size
    :return: List of strings for each chun
    """
    tokens = word_tokenize(text)
    chunks = [tokens[i:i + chunk_size] for i in
              range(0, len(tokens), chunk_size)]

    embed = embed_chunks(chunks)
    return embed


def sentence_based_chunking(text, num_sentences=5):
    """
    Performs sentence-based chunking on the text.
    :param text: Text that is to be chunked
    :param num_sentences: The number of sentences for each chunk
    :return: List of strings for each chunk
    """
    sentences = nltk.sent_tokenize(text)
    chunks = [sentences[i:i + num_sentences] for i in
              range(0, len(sentences), num_sentences)]
    embed = embed_chunks(chunks)
    return embed


# def semantic_chunking(text):
#     """
#     Function for handling semantic chunking.
#     :param text: Text that is to be chunked
#     :return: Embedded chunks
#     """
#     # Tokenize the text
#     tokens = word_tokenize(text)
#     # Perform part-of-speech tagging
#     pos_tags = pos_tag(tokens)

#     # Define a grammar for chunking
#     chunk_grammar = r"""
#         NP: {<DT|JJ|NN.*>+}          # Chunk sequences of DT, JJ, NN
#         VP: {<VB.*><NP|PP|CLAUSE>+$} # Chunk verbs and their arguments
#         PP: {<IN><NP>}               # Chunk prepositions followed by NP
#         CLAUSE: {<NP><VP>}           # Chunk NP, VP
#     """

#     # Create a chunk parser
#     chunk_parser = RegexpParser(chunk_grammar)

#     # Perform chunking
#     chunks = chunk_parser.parse(pos_tags)

#     embed = embed_chunks(chunks)
#     return embed
def semantic_chunking(text):
    tokens = word_tokenize(text)
    pos_tags = pos_tag(tokens)
    
    chunk_grammar = r"""
        NP: {<DT|JJ|NN.*>+}
        VP: {<VB.*><NP|PP|CLAUSE>+$}
        PP: {<IN><NP>}
        CLAUSE: {<NP><VP>}
    """
    chunk_parser = RegexpParser(chunk_grammar)
    chunks = chunk_parser.parse(pos_tags)
    chunk_strings = [' '.join([token for token, tag in chunk.leaves()])
                    for chunk in chunks if hasattr(chunk, 'label')]
    return embed_chunks(chunk_strings)

@app.task(name="chunker")
def chunker_task(json_data):
    """
    Task for chunking a document.
    Simulates chunking a document into parts (chunks).
    :param json_data: JSON file that holds the values for agents.
    :return: Chunked data
    """
    logger.info("Starting chunking task.")
    try:
        # Parse JSON data
        data = json.loads(json_data)
        path = data.get("docsSource", "/shared_data")  # Default to /shared_data if not specified
        
        # Load files from data directory
        texts = load_files(path)
        
        # Process each text
        all_chunks = []
        for text in texts:
            # Perform chunking based on method specified
            if data.get('method') == 'fixed':
                chunks = fixed_size_chunking(text, data.get('chunk_size', 512))
            elif data.get('method') == 'sentence':
                chunks = sentence_based_chunking(text, data.get('num_sentences', 5))
            else:
                chunks = semantic_chunking(text)
            
            # Ensure chunks are JSON serializable
            if isinstance(chunks, np.ndarray):
                chunks = chunks.tolist()
            all_chunks.extend(chunks)
        
        # Ensure the final result is JSON serializable
        return {
            "status": "success", 
            "chunks": all_chunks
        }
        
    except Exception as e:
        logger.error(f"Error in chunking task: {str(e)}")
        return {"status": "error", "message": str(e)}


def send_chunking_task(json_data):
    """
    Helper function to send the chunker task to Celery.
    :param json_data: JSON containing chunker data
    :return: JSON with chunking data
    """
    result = chunker_task.delay(json_data)  # Send task asynchronously
    json_data['chunks'] = result

    return result.get()  # Wait for the result and return it


def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for chunker.")
    worker = celery_worker.worker(app=app)
    options = {
        "loglevel": "DEBUG",
        "traceback": True,
    }

    worker.run(**options)


# Entry point to start the Celery worker or use the app programmatically
if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()