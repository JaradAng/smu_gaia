## **JSON Format Specification**

The inter-agent communication in GAIA is based on a carefully designed JSON structure that encapsulates all necessary project data. This structure is defined by the ProjectData class, which serves as both a data model and a serialization mechanism. The JSON format includes the following fields:

1. id (string): A unique identifier for the project.

2. domain (string): The specific domain or context of the project.

3. docsSource (string): The source of the documents or data being processed.

4. queries (array of strings, optional): A list of queries associated with the project.

5. textData (string, optional): The collected textual data.

6. embedding (string, optional): The chosen embedding method.

7. vectorDB (string, optional): The selected vector database.

8. ragText (string, optional): The generated RAG (Retrieval-Augmented Generation) text.

9. kg
   a. kgTriples (array of strings): The top 5 relevant triples (or more) to be used by Prompt Module.
   b. ner (array of strings): One or more NER techniques used to create the knowledge graph.

10. chunker
    a. chunkingMethod (string, optional): The method chosen for chunking.
    b. chunks (array of strings, optional): The text chunks created during processing.

11. llm
    a. llm (string, optional): The Language Model(s).
    b. llmResult (string, optional): The result produced by the Language Model.

12. prompts
    a. zeroShot (string, optional): The generated zero-shot prompt.
    b. tagBased (string, optional): The generated tag-based prompt.
    c. reasoning (string, optional): The generated reasoning prompt.
    d. custom (array of strings, optional): Any custom prompts generated or provided.

13. vectorDBLoaded (boolean, optional): Indicates if the vector database has been loaded.

14. similarityIndices (object, optional): Stores similarity indices for efficient retrieval.

15. generatedResponse (string, optional): The final generated response.

## **Implementation Details**

The ProjectData class is implemented using Python's dataclass decorator, which automatically generates methods for initialization, representation, and comparison. This class provides several key methods:

1. to_dict(): Converts the object to a dictionary, excluding None values.

2. from_dict(cls, data: dict): Creates a ProjectData object from a dictionary.

3. to_json(): Serializes the object to a JSON string.

4. from_json(cls, json_str: str): Deserializes a JSON string to a ProjectData object.

These methods ensure seamless conversion between the in-memory representation and the JSON format used for communication.

## **Prompts Field Details**

The `prompts` field is a new addition to the JSON structure, designed to store various types of generated prompts. This field enhances the flexibility and clarity of prompt management within the project data. The structure of the `prompts` field is as follows:

```json
"prompts": {
  "zeroShot": "string",
  "tagBased": "string",
  "reasoning": "string",
  "custom": ["string1", "string2", ...]
}
```

- `zeroShot`: Stores a prompt generated without specific examples or context.
- `tagBased`: Stores a prompt that uses specific tags to structure the input.
- `reasoning`: Stores a prompt that encourages step-by-step reasoning.
- `custom`: An array that can store any number of custom prompts.

This structure allows for easy storage and retrieval of different prompt types, facilitating more complex prompt engineering strategies and experiments.
