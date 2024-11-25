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

def extract_triples(textData: str):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(textData)
    triples = []
    
    def get_core_phrase(token):
        """
        Extract the core phrase for a subject or object by excluding determiners and
        prepositional modifiers while keeping essential descriptors.
        """
        logger.info("IN GET CORE PHRASE FUNCTION")
        # Start with the subtree of the token
        words = [t for t in token.subtree if t.dep_ not in {"det", "prep", "punct"}]
        # Join the words to form a clean phrase
        return " ".join([t.text for t in words]).lower()


    for sent in doc.sents:
        logger.info(f"Sentence we are analyzing: {sent}")
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
                    logger.info("IF SUBJ AND OBJ FUNCTION")
                    # Extract core phrases for subject and object
                    subj_phrase = get_core_phrase(subj)
                    obj_phrase = get_core_phrase(obj)

                    # Use the lemma of the predicate for consistency
                    predicate = token.lemma_.lower()

                    # Create the triple
                    triple = (subj_phrase, predicate, obj_phrase)
                    logger.info(f"Triple found in extract_triple: {triple}")
                    triples.append(triple)

    return triples


@app.task(name="graph_db")
def graph_db_task(data):
    """
    Task for Graph DB operations.
    Expects a JSON string containing textData and queries.
    """
    try:
        data_dict = json.loads(data)
        text = data_dict.get("textData", "")
        queries = data_dict.get("queries", [])

        logger.info(f"Graph DB received: {data_dict}")
        logger.info(f"text data: {text}")
        logger.info(f"queries: {queries}")

        # 1. Extract entities and relationships
        triples_list = extract_triples(text)
        logger.info(f"Here are the triples I found: {triples_list}")

        # 2. Create knowledge graph triples and # 3. Store in graph database
        importer = neo()
        importer.import_triples(triples_list)

        # Initializing result structure
        result = {
            "kgTriples": [],
            "ner": ["spacy"]
        }

        for query in queries:
            logger.info("IN QUERY FUNCTION")
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
        return json.dumps({"error": f"Error in Graph DB processing: {str(e)}"})

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