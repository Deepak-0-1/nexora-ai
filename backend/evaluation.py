"""Small deterministic checks for memory retrieval and context assembly."""
from backend.memory import lexical_similarity, cosine

def evaluate_memory_retrieval():
    examples = [
        ("I work as a data engineer using Python", "Data engineer working with Python", True),
        ("I prefer concise answers", "My favorite color is blue", False),
        ("Building a local chatbot with FastAPI", "FastAPI local chatbot project", True),
    ]
    results = []
    for query, memory, expected in examples:
        score = lexical_similarity(query, memory)
        results.append({
            "query": query, "memory": memory,
            "score": round(score, 3), "lexically_related": score > 0.12,
            "expected_related": expected
        })
    return results
