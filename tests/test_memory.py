from backend.memory import lexical_similarity, cosine, should_extract_memory


def test_lexical_similarity_related():
    assert lexical_similarity("Python data engineer", "data engineer uses Python") > 0.2


def test_lexical_similarity_unrelated():
    assert lexical_similarity("weather forecast", "database indexing") == 0


def test_cosine_identical_vectors():
    assert abs(cosine([1, 0], [1, 0]) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors():
    assert cosine([1, 0], [0, 1]) == 0


def test_memory_extraction_gate_accepts_durable_statement():
    assert should_extract_memory("I prefer concise technical explanations.")


def test_memory_extraction_gate_skips_one_off_question():
    assert not should_extract_memory("What is the difference between RAG and fine-tuning?")
