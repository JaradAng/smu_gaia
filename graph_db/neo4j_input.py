from neo4j import GraphDatabase
from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime
from rdflib import Graph
from rdflib_neo4j import Neo4jStoreConfig, Neo4jStore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jTripleImporter:
    def __init__(self):
        """
        Initialize Neo4j connection.
        """
        # set the confguration to connect to your Aura DB
        # TODO: modify uri according to container networking
        self.DB_URI = "bolt://127.0.0.1:7687"
        self.DB_USERNAME = "neo4j"
        self.DB_PWD = ""

        # Configure the Neo4j connection
        self.driver = GraphDatabase.driver(
            uri=self.DB_URI,
            auth=(self.DB_USERNAME, self.DB_PWD)
        )

    def import_triples(self, triples: List[Tuple[str,str,str]]):

        def create_relationship(tx, subj, pred, obj):
            # Create nodes and relationship if they don't exist
            query = """
            MERGE (s:Entity {name: $subj})
            MERGE (o:Entity {name: $obj})
            MERGE (s)-[:RELATIONSHIP {type: $pred}]->(o)
            """
            tx.run(query, subj=subj, pred=pred, obj=obj)

        with self.driver.session() as session:
            for subj, pred, obj in triples:
                session.execute_write(create_relationship, subj, pred, obj)

    def process_question(self, question: str) -> dict:
        """
        Process a natural language question to identify key elements for querying.
        """
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(question.lower())

        query_elements = {
            'focus': None,      # Main topic of question (e.g., "treatments")
            'subject': None,    # Subject of interest (e.g., "diabetes")
            'constraints': [],  # Additional constraints (e.g., "latest", "type 2")
            'question_type': None  # What, How, Who, etc.
        }

        # Identify question type
        for token in doc:
            if token.tag_ == "WDT" or token.tag_ == "WP" or token.tag_ == "WRB":
                query_elements['question_type'] = token.text
                break
            
        # Find main focus and subject
        for chunk in doc.noun_chunks:
            if not query_elements['subject'] and any(word in chunk.text for word in ['diabetes', 'disease', 'condition']):
                query_elements['subject'] = chunk.text
            elif not query_elements['focus'] and any(word in chunk.text for word in ['treatment', 'therapy', 'medication']):
                query_elements['focus'] = chunk.text

        # Identify constraints
        for token in doc:
            if token.pos_ == "ADJ":
                query_elements['constraints'].append(token.text)

        return query_elements

    def generate_neo4j_query(self, query_elements: dict) -> str:
        """
        Convert processed question elements into a Neo4j Cypher query.
        """
        if query_elements['focus'] == 'treatments' or 'treatment' in query_elements['focus']:
            # Query for treatments
            query = """
            MATCH (condition:Entity)-[r:RELATIONSHIP]->(treatment:Entity)
            WHERE condition.name CONTAINS $subject
            AND (r.type CONTAINS 'treats' OR r.type CONTAINS 'used_for')
            """

            # Add constraint for "latest" if present
            if 'latest' in query_elements['constraints']:
                query += """
                AND exists(treatment.date)
                ORDER BY treatment.date DESC
                """

            query += """
            RETURN condition.name as subject, r.type as predicate, treatment.name as object
            LIMIT 5
            """

        else:
            # Generic query pattern
            query = """
            MATCH (s:Entity)-[r:RELATIONSHIP]->(o:Entity)
            WHERE (s.name CONTAINS $subject OR o.name CONTAINS $subject)
            RETURN s.name as subject, r.type as predicate, o.name as object
            LIMIT 5
            """

        return query

    def query_knowledge_graph(self, question: str) -> List[Tuple[str, str, str]]:
        """
        Query the Neo4j knowledge graph using natural language questions.
        """
        # Process the question
        query_elements = self.process_question(question)

        # Generate Neo4j query
        query = self.generate_neo4j_query(query_elements)

        # Execute query
        results = []

        with self.driver.session() as session:
            result = session.run(
                query, 
                subject=query_elements['subject'] if query_elements['subject'] else ''
            )
            for record in result:
                triple = (record["subject"], record["predicate"], record["object"])
                results.append(triple)

        self.driver.close()
        return results
