from pymongo.operations import SearchIndexModel
from db import memories

model = SearchIndexModel(
    name="memory_vector_index",
    type="vectorSearch",
    definition={
        "fields": [
            {"type": "vector", "path": "embedding", "numDimensions": 768, "similarity": "cosine"},
            {"type": "filter", "path": "user_id"},
            {"type": "filter", "path": "status"},
            {"type": "filter", "path": "type"},
        ]
    },
)
print("Created:", memories.create_search_index(model=model))
