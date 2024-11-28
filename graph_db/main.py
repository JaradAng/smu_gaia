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

        # Extract entities and relationships
        triples_list = extract_triples(text)
        logger.info(f"Triples extracted: {triples_list}")

        # Create knowledge graph triples and Store in graph database
        importer = neo()
        importer.import_triples(triples_list)

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