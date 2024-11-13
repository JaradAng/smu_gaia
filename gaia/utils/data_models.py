from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from uuid import uuid4

@dataclass
class KnowledgeGraph:
    kgTriples: List[str] = field(default_factory=list)
    ner: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class ChunkerConfig:
    chunkingMethod: Optional[str] = None
    chunks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class LLMConfig:
    llm: Optional[str] = None
    llmResult: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class ProjectData:
    id: str = field(default_factory=lambda: str(uuid4()))
    domain: str
    docsSource: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Optional fields
    queries: List[str] = field(default_factory=list)
    textData: Optional[str] = None
    embedding: Optional[str] = None
    vectorDB: Optional[str] = None
    ragText: Optional[str] = None
    
    # Nested configurations
    kg: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    chunker: ChunkerConfig = field(default_factory=ChunkerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Status flags and results
    vectorDBLoaded: bool = False
    similarityIndices: Dict[str, Any] = field(default_factory=dict)
    generatedResponse: Optional[str] = None
    status: str = "created"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the ProjectData instance to a dictionary, excluding None values."""
        data = {}
        for field_name, field_value in asdict(self).items():
            if field_value is not None:
                if isinstance(field_value, (KnowledgeGraph, ChunkerConfig, LLMConfig)):
                    data[field_name] = field_value.to_dict()
                else:
                    data[field_name] = field_value
        return data

    def to_json(self) -> str:
        """Convert the ProjectData instance to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectData':
        """Create a ProjectData instance from a dictionary."""
        # Handle nested objects
        if 'kg' in data:
            data['kg'] = KnowledgeGraph(**data['kg'])
        if 'chunker' in data:
            data['chunker'] = ChunkerConfig(**data['chunker'])
        if 'llm' in data:
            data['llm'] = LLMConfig(**data['llm'])
        
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'ProjectData':
        """Create a ProjectData instance from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    def update(self, **kwargs) -> None:
        """Update the ProjectData instance with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow().isoformat()

    def validate(self) -> bool:
        """Validate the ProjectData instance."""
        required_fields = ['id', 'domain', 'docsSource']
        return all(hasattr(self, field) and getattr(self, field) for field in required_fields)

# Example usage class
class ProjectDataManager:
    def create_project(self, domain: str, docs_source: str, **kwargs) -> ProjectData:
        """Create a new project with the given parameters."""
        project = ProjectData(
            domain=domain,
            docsSource=docs_source,
            **kwargs
        )
        return project

    def update_project_status(self, project: ProjectData, new_status: str) -> None:
        """Update the project status and trigger any necessary side effects."""
        project.status = new_status
        project.updated_at = datetime.utcnow().isoformat()