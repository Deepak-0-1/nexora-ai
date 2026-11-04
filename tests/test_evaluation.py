from backend.evaluation import evaluate_memory_retrieval


def test_evaluation_examples_have_expected_relation():
    results = evaluate_memory_retrieval()
    assert len(results) == 3
    assert results[0]["lexically_related"] is True
    assert results[1]["lexically_related"] is False
