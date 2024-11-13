from celery import Celery
from celery.bin import worker as celery_worker
import logging
import os
import json
import random
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Celery(
    "gaia",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
)

@dataclass
class KG:
    kgTriples: List[str]
    ner: List[str]

@dataclass
class Chunker:
    chunkingMethod: Optional[str] = None
    chunks: Optional[List[str]] = None

@dataclass
class LLM:
    llm: Optional[str] = None
    llmResult: Optional[str] = None

@dataclass
class Prompts:
    zeroShot: Optional[str] = None
    tagBased: Optional[str] = None
    reasoning: Optional[str] = None
    custom: Optional[List[str]] = None

@dataclass
class ProjectData:
    id: str
    domain: str
    docsSource: str
    queries: Optional[List[str]] = None
    textData: Optional[str] = None
    embedding: Optional[str] = None
    vectorDB: Optional[str] = None
    ragText: Optional[str] = None
    kg: KG = field(default_factory=KG)
    chunker: Chunker = field(default_factory=Chunker)
    llm: LLM = field(default_factory=LLM)
    prompts: Prompts = field(default_factory=Prompts)
    vectorDBLoaded: Optional[bool] = None
    similarityIndices: Optional[dict] = None
    generatedResponse: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict):
        try:
            return cls(**data)
        except TypeError as e:
            raise ValueError(f"Invalid data structure: {str(e)}")

    def to_json(self):
        try:
            return json.dumps(self.to_dict(), indent=2)
        except TypeError as e:
            raise ValueError(f"Cannot serialize to JSON: {str(e)}")

    @classmethod
    def from_json(cls, json_str: str):
        try:
            return cls.from_dict(json.loads(json_str))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {str(e)}")

def generate_zero_shot_prompt(project_data: ProjectData) -> str:
    try:
        prompt = f"Based on the following data:\n"
        prompt += f"Text: {project_data.ragText}\n"
        prompt += f"Knowledge Graph Triples: {', '.join(project_data.kg.kgTriples)}\n"
        prompt += f"What is {project_data.queries[0] if project_data.queries else 'the main topic'}"
        return prompt
    except AttributeError as e:
        raise ValueError(f"Missing required attribute in ProjectData: {str(e)}")

def generate_tag_based_prompt(project_data: ProjectData) -> str:
    try:
        tags = ["<instruction>", "<context>", "<input>", "<output>"]
        selected_tags = random.sample(tags, 3)
        prompt = f"{selected_tags[0]} Answer the following question based on the provided information.\n"
        prompt += f"{selected_tags[1]} Domain: {project_data.domain}\n"
        prompt += f"Text: {project_data.ragText}\n"
        prompt += f"Knowledge Graph Triples: {', '.join(project_data.kg.kgTriples)}\n"
        prompt += f"{selected_tags[2]} {project_data.queries[0] if project_data.queries else 'What is the main topic?'}"
        return prompt
    except AttributeError as e:
        raise ValueError(f"Missing required attribute in ProjectData: {str(e)}")

def generate_reasoning_prompt(project_data: ProjectData) -> str:
    try:
        prompt = "<instruction> Answer the following question based on the provided information.\n"
        prompt += f"<context> Domain: {project_data.domain}\n"
        prompt += f"Text: {project_data.ragText}\n"
        prompt += f"Knowledge Graph Triples: {', '.join(project_data.kg.kgTriples)}\n"
        prompt += f"<input> {project_data.queries[0] if project_data.queries else 'What is the main topic?'}\n"
        prompt += "<reasoning> Explain your thought process step by step.\n"
        prompt += "<thinking> Break down the problem and analyze it systematically."
        return prompt
    except AttributeError as e:
        raise ValueError(f"Missing required attribute in ProjectData: {str(e)}")

@app.task(name="prompt", bind=True, max_retries=3)
def prompt_task(self, data):
    """
    Task for enhancing a prompt.
    Generates three types of prompts based on the input data.
    """
    logger.info(f"Prompt received: {data}")

    try:
        project_data = ProjectData.from_json(data)
        
        project_data.prompts.zeroShot = generate_zero_shot_prompt(project_data)
        project_data.prompts.tagBased = generate_tag_based_prompt(project_data)
        project_data.prompts.reasoning = generate_reasoning_prompt(project_data)
        
        enhanced_prompt = project_data.to_json()

        logger.info(f"Prompts generated: {project_data.prompts}")
        return enhanced_prompt
    except ValueError as e:
        logger.error(f"Invalid input data: {str(e)}")
        return json.dumps({"error": f"Invalid input data: {str(e)}"})
    except AttributeError as e:
        logger.error(f"Missing required attribute: {str(e)}")
        return json.dumps({"error": f"Missing required attribute: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        self.retry(exc=e, countdown=60)  # Retry after 60 seconds

def send_prompt_task(data):
    """
    Helper function to send the prompt task to Celery.
    """
    try:
        result = prompt_task.delay(data)
        return result.get(timeout=300)  # 5 minutes timeout
    except Exception as e:
        logger.error(f"Error sending prompt task: {str(e)}")
        return json.dumps({"error": f"Error sending prompt task: {str(e)}"})

def start_celery_worker():
    """
    Start the Celery worker programmatically.
    """
    logger.info("Starting Celery worker for prompt task.")
    worker = celery_worker.worker(app=app)
    options = {
        "loglevel": "INFO",
        "traceback": True,
    }

    try:
        worker.run(**options)
    except Exception as e:
        logger.error(f"Error starting Celery worker: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting Celery app.")
    try:
        app.start()
    except Exception as e:
        logger.error(f"Error starting Celery app: {str(e)}")
