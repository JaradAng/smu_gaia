import random
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json
from gaia.utils.data_models import KG, Chunker, LLM, Prompts, ProjectData


def generate_zero_shot_prompt(project_data: ProjectData) -> str:
    prompt = f"Based on the following data:\n"
    prompt += f"Text: {project_data.ragText}\n"
    prompt += f"Knowledge Graph Triples: {', '.join(project_data.kg.kgTriples)}\n"
    prompt += f"What is {project_data.queries[0] if project_data.queries else 'the main topic'}"
    return prompt

def generate_tag_based_prompt(project_data: ProjectData) -> str:
    tags = ["<instruction>", "<context>", "<input>", "<output>"]
    selected_tags = random.sample(tags, 3)
    prompt = f"{selected_tags[0]} Answer the following question based on the provided information.\n"
    prompt += f"{selected_tags[1]} Domain: {project_data.domain}\n"
    prompt += f"Text: {project_data.ragText}\n"
    prompt += f"Knowledge Graph Triples: {', '.join(project_data.kg.kgTriples)}\n"
    prompt += f"{selected_tags[2]} {project_data.queries[0] if project_data.queries else 'What is the main topic?'}"
    return prompt

def generate_reasoning_prompt(project_data: ProjectData) -> str:
    prompt = "<instruction> Answer the following question based on the provided information.\n"
    prompt += f"<context> Domain: {project_data.domain}\n"
    prompt += f"Text: {project_data.ragText}\n"
    prompt += f"Knowledge Graph Triples: {', '.join(project_data.kg.kgTriples)}\n"
    prompt += f"<input> {project_data.queries[0] if project_data.queries else 'What is the main topic?'}\n"
    prompt += "<reasoning> Explain your thought process step by step.\n"
    prompt += "<thinking> Break down the problem and analyze it systematically."
    return prompt 