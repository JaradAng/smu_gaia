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
        # set the confguration to connect to your Aura DB
        logger.info(f"In Neo4j triple importer")
        # TODO: modify uri according to container networking
        self.DB_URI = "bolt://host.docker.internal:7687"
        self.DB_USERNAME = "neo4j"
        self.DB_PWD = "neo4j"

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

        logger.info(f"importing triples into KG")
        def create_relationship(tx, subj, pred, obj):
            # Create nodes and relationship if they don't exist
            query = """
            MERGE (s:Entity {name: $subj})
            MERGE (o:Entity {name: $obj})
            MERGE (s)-[:RELATIONSHIP {type: $pred}]->(o)
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

    def process_question(self, question: str, use_dependency_parsing: bool = True) -> Dict[str, Any]:
        """
        Process a natural language question to extract query elements.

        :param question: The natural language question.
        :param use_dependency_parsing: Whether to use dependency parsing for extraction.
        """
        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(question.lower())

            query_elements = {
                'focus': None,
                'subject': None,
                'constraints': [],
                'question_type': None
            }

            # Identify question type
            for token in doc:
                if token.tag_ in {"WDT", "WP", "WRB"}:
                    query_elements['question_type'] = token.text
                    break

            # Extract focus and subject
            if use_dependency_parsing:
                self.extract_focus_and_subject_with_dependencies(doc, query_elements)
            else:
                for chunk in doc.noun_chunks:
                    if not query_elements['subject'] and any(word in chunk.text for word in ['diabetes', 'disease', 'condition']):
                        query_elements['subject'] = chunk.text
                    elif not query_elements['focus'] and any(word in chunk.text for word in ['treatment', 'therapy', 'medication']):
                        query_elements['focus'] = chunk.text

            # Identify constraints
            for token in doc:
                if token.pos_ == "ADJ":
                    query_elements['constraints'].append(token.text)

            logger.info(f"Processed question: {query_elements}")
            return query_elements
        except Exception as e:
            logger.error(f"Failed to process question: {e}")
            return {}

    def generate_neo4j_query(self, query_elements: Dict[str, Any]) -> str:
        """
        Generate a Cypher query based on processed question elements.
        """
        try:
            if query_elements.get('focus') in {'treatment', 'treatments'}:
                query = """
                MATCH (condition:Entity)-[r:RELATIONSHIP]->(treatment:Entity)
                WHERE condition.name CONTAINS $subject
                AND (r.type CONTAINS 'treats' OR r.type CONTAINS 'used_for')
                """
                if 'latest' in query_elements.get('constraints', []):
                    query += """
                    AND exists(treatment.date)
                    ORDER BY treatment.date DESC
                    """
                query += """
                RETURN condition.name as subject, r.type as predicate, treatment.name as object
                LIMIT 5
                """
            else:
                query = """
                MATCH (s:Entity)-[r:RELATIONSHIP]->(o:Entity)
                WHERE (s.name CONTAINS $subject OR o.name CONTAINS $subject)
                RETURN s.name as subject, r.type as predicate, o.name as object
                LIMIT 5
                """
            return query
        except Exception as e:
            logger.error(f"Failed to generate Neo4j query: {e}")
            return ""

    def query_knowledge_graph(self, question: str, use_dependency_parsing: bool = True) -> List[Tuple[str, str, str]]:
        """
        Query the Neo4j knowledge graph using a natural language question.

        :param question: The natural language question.
        :param use_dependency_parsing: Whether to use dependency parsing for extraction.
        """
        try:
            query_elements = self.process_question(question, use_dependency_parsing)
            cypher_query = self.generate_neo4j_query(query_elements)

            results = []
            with self.driver.session() as session:
                result = session.run(cypher_query, subject=query_elements.get('subject', ''))
                for record in result:
                    results.append((record["subject"], record["predicate"], record["object"]))
            logger.info(f"Query returned {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Failed to query knowledge graph: {e}")
            return []