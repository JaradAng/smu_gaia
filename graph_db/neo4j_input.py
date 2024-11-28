from neo4j import GraphDatabase
from typing import List, Dict, Any, Tuple
import logging
import spacy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jTripleImporter:
    def __init__(self):
        """
        Initialize Neo4j connection.
        """
        self.DB_URI = "bolt://neo4j:7687"
        self.DB_USERNAME = "neo4j"
        self.DB_PWD = "gaiaadmin"

        try:
            self.driver = GraphDatabase.driver(
                uri=self.DB_URI,
                auth=(self.DB_USERNAME, self.DB_PWD)
            )
            logger.info("Connected to Neo4j database.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """
        Close the Neo4j connection.
        """
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed.")

    def import_triples(self, triples: List[Tuple[str,str,str]]):

        def create_relationship(tx, subj, pred, obj):
            # Create nodes and relationship if they don't exist
            query = f"""
            MERGE (s:Entity {{name: $subj}})
            MERGE (o:Entity {{name: $obj}})
            MERGE (s)-[r:{pred}]->(o)
            """
            tx.run(query, subj=subj, pred=pred, obj=obj)

        try:
            with self.driver.session() as session:
                for subj, pred, obj in triples:
                    session.write_transaction(create_relationship, subj, pred, obj)
            logger.info(f"Imported {len(triples)} triples successfully.")
        except Exception as e:
            logger.error(f"Failed to import triples: {e}")

    def extract_focus_and_subject_with_dependencies(self, doc, query_elements: dict) -> None:
        """
        Extract focus and subject dynamically using dependency parsing.

        :param doc: The SpaCy processed document.
        :param query_elements: The dictionary to store extracted elements.
        """
        for token in doc:
            # Identify subject based on dependency role
            if token.dep_ in {'nsubj', 'nsubjpass'} and not query_elements['subject']:
                query_elements['subject'] = token.text

            # Identify focus as a direct object or attribute
            elif token.dep_ in {'dobj', 'attr', 'pobj'} and not query_elements['focus']:
                query_elements['focus'] = token.text

    def process_question(self, question) -> Dict[str, Any]:
        """
        Process a natural language question to extract query elements.

        :param question: The natural language question.
        :param use_dependency_parsing: Whether to use dependency parsing for extraction.
        """
        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(question.lower())

            query_elements = {
                'subject': None,
                'predicate': None,
                'object': None,
                'constraints': [],
                'question_type': None
            }

            # Identify question type
            for token in doc:
                if token.tag_ in {"WDT", "WP", "WRB"}:
                    query_elements['question_type'] = token.text
                    break

            # Extract subject, predicate, and object dynamically
            for chunk in doc.noun_chunks:
                if not query_elements['subject']:
                    query_elements['subject'] = chunk.text
                elif not query_elements['object']:
                    query_elements['object'] = chunk.text

            # TO DO: Fix perdicate finding algorithm. All predicates show as None. 
            for token in doc:
                # Identify verbs as potential predicates
                if token.pos_ == "VERB" and not query_elements['predicate']:
                    query_elements['predicate'] = token.lemma_
                # Add constraints dynamically
                if token.dep_ == "amod" or token.pos_ == "ADJ":
                    query_elements['constraints'].append(token.text)

            logger.info(f"Processed question: {question}")
            return query_elements
        except Exception as e:
            logger.error(f"Failed to process question: {e}")
            return {}

    def generate_neo4j_query(self, query_elements: Dict[str, Any], question:str) -> str:
        """
        Generate a dynamic Cypher query from extracted elements.
        """
        nlp = spacy.load("en_core_web_sm")

        try:
            subject = query_elements.get('subject', '')
            predicate = query_elements.get('predicate', '')
            obj = query_elements.get('object', '')

            logger.info(f"In generate function, this is subject: {subject} and this is object:{obj}")
            if subject and obj:
                query = """
                CALL db.index.fulltext.queryNodes("entityNameIndex", $subject + " " + $object) YIELD node AS s
                WITH s
                MATCH (s)-[r]->(o:Entity)
                WHERE 
                ($subject IS NOT NULL AND apoc.text.sorensenDiceSimilarity(s.name, $subject) > 0.6) OR
                ($object IS NOT NULL AND apoc.text.sorensenDiceSimilarity(o.name, $object) > 0.6) OR
                ($subject IS NOT NULL AND apoc.text.sorensenDiceSimilarity(o.name, $subject) > 0.6) OR
                ($object IS NOT NULL AND apoc.text.sorensenDiceSimilarity(s.name, $object) > 0.6)
                RETURN 
                s.name AS subject, 
                type(r) AS predicate, 
                o.name AS object
                LIMIT 10
                        """
                return query
            else:
                keywords = [
                    token.lemma_ for token in nlp(question.lower()) 
                    if token.pos_ in {"NOUN", "PROPN", "ADJ"} 
                    and len(token.lemma_) > 2  # Ignore very short words
                ]
                keywords = list(set(keywords))
                if len(keywords) != 0:
                    query="""
                    UNWIND $keywords AS keyword
                    MATCH (s:Entity)-[r]->(o:Entity)
                    WHERE 
                        apoc.text.sorensenDiceSimilarity(s.name, keyword) > $threshold OR
                        apoc.text.sorensenDiceSimilarity(o.name, keyword) > $threshold
                    RETURN DISTINCT 
                        s.name AS subject, 
                        type(r) AS predicate, 
                        o.name AS object
                    LIMIT 10
                    """
                    return query
                else:
                    return ""
        except Exception as e:
            logger.error(f"Failed to generate Neo4j query: {e}")
            return ""

    def create_index(self):
        with self.driver.session() as session:
            session.run("CREATE FULLTEXT INDEX entityNameIndex FOR (n:Entity) ON EACH [n.name];")
        logger.info(f"Index 'entityNameIndex' created.")

    def query_knowledge_graph(self, question: str) -> List[Tuple[str, str, str]]:
        """
        Query the Neo4j knowledge graph using a natural language question.
        :param question: The natural language question.
        """
        try:
            query_elements = self.process_question(question)
            logger.info(f"Current query elements {query_elements}")
            cypher_query = self.generate_neo4j_query(query_elements, question)

            results = []
            with self.driver.session() as session:
                result = session.run(
                    cypher_query, 
                    subject=query_elements.get('subject', ''),
                    predicate=query_elements.get('predicate'),
                    object=query_elements.get('object')
                )
                for record in result:
                    results.append((record["subject"], record["predicate"], record["object"]))
            logger.info(f"Query returned {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Failed to query knowledge graph: {e}")
            return []