import asyncio
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
)


@app.task(name="graph_db")
def parse_json_data(data: str):
    """
    Parse JSON string and extract KG-related information.
    """
    try:
        if isinstance(data, str):
            parsed_data = json.loads(data)
        else:
            parsed_data = data
        return parsed_data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        return None

def extract_triples(textData: str):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(textData)
    triples = []

    for sent in doc.sents:
        for token in sent:
            # Look for verbs as they often represent relationships
            if token.pos_ == "VERB":
                # Find subject
                subj = None
                for child in token.lefts:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        subj = child
                        break

                # Find object
                obj = None
                for child in token.rights:
                    if child.dep_ in ["dobj", "pobj"]:
                        obj = child
                        break

                # If we have both subject and object, add the triple
                if subj and obj:
                    triple = (
                        subj.text.lower(),  # Corrected: Use .text
                        token.text.lower(),  # Corrected: Use .text
                        obj.text.lower()     # Corrected: Use .text
                    )
                    triples.append(triple)

    return triples

@app.task(name='graph_db_task')
def graph_db_task(data):
    """
    Task for Graph DB operations.
    Expects a JSON string containing textData and queries.
    """
    data = parse_json_data(data)
    if not data:
        logger.error("Failed to parse data")
        return None

    textData = data.get('textData', "")
    queries = data.get('queries', [])

    logger.info(f"Graph DB received: {data}")
    logger.info(f"text data: {textData}")
    logger.info(f"queries: {queries}")

    triples_list = extract_triples(textData)
    importer = neo()
    
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])
        
        # Simulated knowledge graph processing (replace with actual KG logic)
        # Here you would typically:
        # 1. Extract entities and relationships
        # 2. Create knowledge graph triples
        # 3. Store in graph database
        
        result = {
            "kgTriples": [
                "entity1 - relation1 - entity2",
                "entity2 - relation2 - entity3",
                "entity1 - relation3 - entity4",
                "entity3 - relation4 - entity5",
                "entity4 - relation5 - entity5"
            ],
            "ner": ["spacy", "nltk"],  # List of NER techniques used
        }
        
        logger.info(f"Graph DB produced: {result}")
        return json.dumps(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {str(e)}")
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        logger.error(f"Error in Graph DB processing: {str(e)}")
        return json.dumps({"error": f"Error in Graph DB processing: {str(e)}"})

        importer.import_triples(triples_list)
        result = {}
        for query in queries:
            result[query] = importer.query_knowledge_graph(query)
    except Exception as e:
        logger.error(f"Error during Neo4j operations: {e}")
        return None

    logger.info(f"Graph DB produced: {result}")
    return result

async def send_graph_db_task(data):
    """
    Helper function to send the graph DB task to Celery asynchronously.
    """
    result = graph_db_task.delay(data)  # Send task asynchronously

    # Use asyncio to wait for the result without blocking
    while not result.ready():
        await asyncio.sleep(0.1)  # Non-blocking wait for 100ms

    return result.result

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