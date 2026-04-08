from zhicore.kg import extract_chunk_schema


def test_kg_extraction_filters_generic_terms_and_limits_edges() -> None:
    text = (
        "This paper proposes a method and shows results for a system.\n"
        "FastAPI is a framework for building APIs.\n"
        "GraphRAG is a type of retrieval method used in LearnOS.\n"
        "In general, the method is effective and the system is robust.\n"
    )
    schema = extract_chunk_schema(text)

    # Node hygiene expectation: generic academic words should not dominate the concept list.
    concepts_lower = {item.lower() for item in schema["concepts"]}
    assert "system" not in concepts_lower
    assert "method" not in concepts_lower
    assert "results" not in concepts_lower

    # Edge hygiene expectation: extraction should avoid producing a hairball of weak relations.
    relations = schema["relations"]
    related_edges = [edge for edge in relations if edge["type"] == "related-to"]
    assert len(related_edges) <= 2
