from celery import Celery
from celery.bin import worker as celery_worker
import nltk
from nltk import word_tokenize, pos_tag
from nltk.chunk import RegexpParser
import logging
import os
import json

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)

nltk.download('punkt_tab')


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
    :return: List of Tensors
    """
    # Load pre-trained Sentence-BERT model
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    # Generate embeddings for each chunk
    embeddings = model.encode(chunks)

    return embeddings


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


def semantic_chunking(text):
    """
    Function for handling semantic chunking.
    :param text: Text that is to be chunked
    :return: Embedded chunks
    """
    # Tokenize the text
    tokens = word_tokenize(text)

    # Perform part-of-speech tagging
    pos_tags = pos_tag(tokens)

    # Define a grammar for chunking
    chunk_grammar = r"""
        NP: {<DT|JJ|NN.*>+}          # Chunk sequences of DT, JJ, NN
        VP: {<VB.*><NP|PP|CLAUSE>+$} # Chunk verbs and their arguments
        PP: {<IN><NP>}               # Chunk prepositions followed by NP
        CLAUSE: {<NP><VP>}           # Chunk NP, VP
    """

    # Create a chunk parser
    chunk_parser = RegexpParser(chunk_grammar)

    # Perform chunking
    chunks = chunk_parser.parse(pos_tags)

    embed = embed_chunks(chunks)
    return embed


@app.task(name="chunker")
def chunker_task(json_data):
    """
    Task for chunking a document.
    Expects a JSON string containing textData and optional chunkingMethod.
    """
    logger.info(f"Chunker received: {data}")
    
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        method = data_dict.get("chunkingMethod", "paragraph")
        
        # Simulated chunking (replace with actual chunking logic)
        chunks = [text[i:i+100] for i in range(0, len(text), 100)]
        
        result = {
            "chunkingMethod": method,
            "chunks": chunks
        }
        
        logger.info(f"Chunker produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error processing chunks: {str(e)}")
        return json.dumps({"error": f"Error processing chunks: {str(e)}"})


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
