from collections import defaultdict
from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import spacy
import json
from neo4j_input import Neo4jTripleImporter as neo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

def extract_triples(textData: str):
    # Load spaCy model
    nlp = spacy.load("en_core_web_sm")
    
    # Process the entire text
    doc = nlp(textData)
    
    triples = []
    
    # Store potential antecedents
    last_noun_phrase = None

    def get_comprehensive_noun_phrase(token):
        """
        Extract a comprehensive noun phrase, preserving contextual information
        """
        # If token is a pronoun, try to use the last known noun phrase
        if token.pos_ == "PRON" and last_noun_phrase:
            return last_noun_phrase
        
        # Collect all words in the token's subtree
        words = [t for t in token.subtree]
        
        # Focus on words that contribute meaningful information
        meaningful_words = [
            t.text for t in words 
            if t.pos_ in {"NOUN", "PROPN", "ADJ"} or 
               t.dep_ in {"compound", "amod", "nn"}
        ]
        
        # If meaningful words exist, join them
        if meaningful_words:
            phrase = " ".join(meaningful_words)
            return phrase.lower().strip()
        
        # Fallback to the token's text
        return token.text.lower().strip()

    for sent in doc.sents:
        for token in sent:
            # Include both regular verbs and participles
            if token.pos_ in ["VERB", "AUX"] or (token.pos_ == "ADJ" and token.dep_ == "acomp"):
                # Find subject
                subj = None
                for child in token.head.lefts if token.dep_ == "acomp" else token.lefts:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        subj = child
                        break

                # Find object - include more object types
                obj = None
                for child in token.rights:
                    if child.dep_ in ["dobj", "pobj", "attr"]:
                        obj = child
                        break
                    # Handle prepositional phrases
                    elif child.dep_ == "prep":
                        for grandchild in child.children:
                            if grandchild.dep_ == "pobj":
                                obj = grandchild
                                break
                        if obj:
                            break

                # If we have both subject and object, add the triple
                if subj and obj:
                    # Extract comprehensive phrases for subject and object
                    subj_phrase = get_comprehensive_noun_phrase(subj)
                    obj_phrase = get_comprehensive_noun_phrase(obj)

                    # Update last known noun phrase
                    if subj.pos_ in {"NOUN", "PROPN"}:
                        last_noun_phrase = subj_phrase

                    # Use the lemma of the predicate for consistency
                    predicate = token.lemma_.lower()

                    # Create the triple
                    triple = (subj_phrase, predicate, obj_phrase)
                    triples.append(triple)

    return triples


def load_files(directory):
    """
    Loads in text files in specified directory.
    :param directory: Directory holding files
    :return: Combined text from all files
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory {directory} does not exist")
        return ""
        
    texts = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            try:
                with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                    texts.append(f.read())
            except Exception as e:
                logger.error(f"Error reading file {filename}: {str(e)}")
                continue
    
    # Combine texts with spacing
    full_text = ""
    for text in texts:
        full_text += text + "\n\n"
    return full_text.strip()  # Remove trailing newlines


@app.task(name="graph_db")
def graph_db_task(json_data):
    """
    Task for processing text data and creating a knowledge graph.
    :param json_data: JSON containing docsSource and queries
    :return: JSON with graph data
    """
    logger.info(f"Graph DB received: {json_data}")
    try:
        # Parse JSON data
        data = json.loads(json_data)
        docs_source = data.get("docsSource", "/shared_data")  # Default to /shared_data if not specified
        
        # Load and process text
        logger.info(f"Loading text from directory: {docs_source}")
        text_data = load_files(docs_source)
        
        if not text_data:
            logger.warning("No text data provided or found in files")
            
        queries = data.get("queries", [])
        
        # Extract triples from text
        triples = extract_triples(text_data)
        logger.info(f"Triples extracted: {triples}")

        # Create knowledge graph triples and Store in graph database
        importer = neo()
        importer.import_triples(triples)

        # Initializing result structure
        result = {
            "kgTriples": [],
            "ner": ["spacy"]
        }

        importer.create_index()
        for query in queries:
            kg_triples = importer.query_knowledge_graph(query)

            formatted_kg_triples = [f"{subject} - {relation} - {object}" 
                        for subject, relation, object in kg_triples]
            
            result["kgTriples"].extend(formatted_kg_triples)

        # Remove duplicates
        result["kgTriples"] = list(dict.fromkeys(result["kgTriples"]))

        logger.info(f"Graph DB produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error in Graph DB processing: {str(e)}")
        # return json.dumps({"error": f"Error in Graph DB processing: {str(e)}"})
        raise e

def send_graph_db_task(data):
    """
    Helper function to send the graph DB task to Celery.
    """
    result = graph_db_task.delay(data)  # Send task asynchronously
    return result.get()  # Wait for the result and return it

def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for graph DB.")
    worker = celery_worker.worker(app=app)  # Create worker instance
    options = {
        "loglevel": "INFO",
        "traceback": True,
    }

    worker.run(**options)


if __name__ == "__main__":
    logger.info("Starting Celery app.")
    app.start()