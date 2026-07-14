"""Unit tests for the advanced RAG chunking strategies."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import pytest

from matemium.intelligence.chunking import (
    CHUNKING_METHODS,
    autodetect_and_chunk,
    sentence_tokenize,
    fixed_size_chunking,
    recursive_character_chunking,
    semantic_chunking,
    document_specific_chunking,
    hierarchical_chunking,
    sentence_aware_chunking,
    token_based_chunking,
    sliding_window_chunking,
    topic_based_chunking,
    proposition_based_chunking,
    context_aware_chunking,
    agentic_chunking,
    small_to_big_chunking,
    statistical_chunking,
    modality_specific_chunking,
)

# Mock embedding model for testing ML-based paths
class MockEmbeddingModel:
    def encode(self, texts: list[str], convert_to_numpy: bool = True) -> Any:
        import numpy as np
        # Return a simple deterministic embedding for each text
        # Make them slightly different so they don't have exactly 1.0 similarity
        embeddings = []
        for i, text in enumerate(texts):
            vec = np.zeros(768)
            vec[i % 768] = 1.0
            embeddings.append(vec)
        return np.array(embeddings)


# Mock LLM client for agentic & proposition-based testing
class MockLLMClient:
    def complete(self, prompt: str) -> str:
        if "propositions" in prompt:
            return "- Fact 1: AI is useful\n- Fact 2: Python is elegant\n- Fact 3: Testing is crucial"
        elif "chunk boundaries" in prompt:
            return "Section A---CHUNK---Section B---CHUNK---Section C"
        return "Standard response"


@pytest.fixture
def sample_text() -> str:
    return (
        "Retrieval-Augmented Generation (RAG) is highly powerful. "
        "It combines search with generative models. "
        "Chunking is a critical step in building robust RAG systems. "
        "It helps preserve semantic relationships and optimize token usage. "
        "Always evaluate your chunking method under representative workloads."
    )


def test_sentence_tokenize(sample_text: str):
    sentences = sentence_tokenize(sample_text)
    assert len(sentences) == 5
    assert sentences[0]["text"] == "Retrieval-Augmented Generation (RAG) is highly powerful."
    assert sentences[1]["text"] == "It combines search with generative models."


def test_fixed_size_chunking(sample_text: str):
    chunks = fixed_size_chunking(sample_text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"]) <= 100
        assert chunk["metadata"]["method"] == "fixed_size"
        assert "start_char" in chunk["metadata"]
        assert "end_char" in chunk["metadata"]


def test_recursive_character_chunking(sample_text: str):
    chunks = recursive_character_chunking(sample_text, chunk_size=150, overlap=30)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"]) <= 150
        assert chunk["metadata"]["method"] == "recursive"


def test_semantic_chunking_fallback(sample_text: str):
    # Testing zero-dependency fallback (no model passed)
    chunks = semantic_chunking(sample_text, breakpoint_threshold_amount=50.0)
    assert len(chunks) >= 1


def test_semantic_chunking_with_model(sample_text: str):
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        pytest.skip("numpy is required for semantic chunking with model test")

    model = MockEmbeddingModel()
    chunks = semantic_chunking(sample_text, breakpoint_threshold_amount=50.0, embedding_model=model)
    assert len(chunks) > 0
    assert any(c["metadata"]["method"] == "semantic" for c in chunks)


def test_document_specific_chunking_python():
    py_code = (
        "# ---DIV: Introduction---\n"
        "class Animator:\n"
        "    def animate(self):\n"
        "        pass\n\n"
        "def render_scene():\n"
        "    return 42\n"
    )
    chunks = document_specific_chunking(py_code, file_type="python")
    assert len(chunks) >= 2
    assert any("class Animator" in c["text"] for c in chunks)
    assert any("def render_scene" in c["text"] for c in chunks)


def test_document_specific_chunking_markdown():
    md_doc = (
        "# Main Heading\n"
        "Some introductory text about physics.\n"
        "## Part 1: Waves\n"
        "Waves transmit energy without matter transport.\n"
        "## Part 2: Particles\n"
        "Particles possess mass and momentum.\n"
    )
    chunks = document_specific_chunking(md_doc, file_type="markdown")
    assert len(chunks) >= 2
    assert any("Main Heading" in c["metadata"].get("header", "") for c in chunks)
    assert any("Waves" in c["metadata"].get("header", "") for c in chunks)


def test_hierarchical_chunking(sample_text: str):
    chunks = hierarchical_chunking(sample_text, parent_chunk_size=150, child_chunk_size=50)
    assert len(chunks) > 0
    for chunk in chunks:
        meta = chunk["metadata"]
        assert meta["method"] == "hierarchical"
        assert "parent_text" in meta
        assert "parent_index" in meta
        assert "child_index" in meta


def test_sentence_aware_chunking(sample_text: str):
    chunks = sentence_aware_chunking(sample_text, max_chunk_size=120, overlap_sentences=1)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["metadata"]["method"] == "sentence_aware"
        # Verify that we don't break sentences
        # Splitting by space should contain the whole original sentence words
        for s in sentence_tokenize(chunk["text"]):
            assert s["text"] in sample_text


def test_token_based_chunking(sample_text: str):
    # Test token_based_chunking fallback/approximate words mode
    chunks = token_based_chunking(sample_text, chunk_size_tokens=15, overlap_tokens=5)
    assert len(chunks) > 0
    for chunk in chunks:
        assert "method" in chunk["metadata"]


def test_sliding_window_chunking(sample_text: str):
    chunks = sliding_window_chunking(sample_text, window_size=100, step_size=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["metadata"]["method"] == "sliding_window"


def test_topic_based_chunking(sample_text: str):
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        pytest.skip("numpy is required for topic based chunking test")

    model = MockEmbeddingModel()
    chunks = topic_based_chunking(sample_text, n_topics=2, embedding_model=model)
    assert len(chunks) > 0


def test_proposition_based_chunking(sample_text: str):
    # Rule fallback testing
    chunks = proposition_based_chunking(sample_text)
    assert len(chunks) > 0
    
    # LLM testing
    llm = MockLLMClient()
    llm_chunks = proposition_based_chunking(sample_text, llm_client=llm)
    assert len(llm_chunks) > 0
    assert any("AI is useful" in c["text"] for c in llm_chunks)


def test_context_aware_chunking(sample_text: str):
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        pytest.skip("numpy is required for context aware chunking test")

    model = MockEmbeddingModel()
    chunks = context_aware_chunking(sample_text, embedding_model=model)
    assert len(chunks) > 0


def test_agentic_chunking(sample_text: str):
    llm = MockLLMClient()
    chunks = agentic_chunking(sample_text, llm_client=llm)
    assert len(chunks) > 0
    assert any("Section A" in c["text"] for c in chunks)


def test_small_to_big_chunking(sample_text: str):
    chunks = small_to_big_chunking(sample_text, child_size=100, parent_size=300)
    assert len(chunks) > 0
    for chunk in chunks:
        assert "parent_context" in chunk["metadata"]
        assert chunk["text"] in chunk["metadata"]["parent_context"]


def test_statistical_chunking(sample_text: str):
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        pytest.skip("numpy is required for statistical chunking test")

    model = MockEmbeddingModel()
    chunks = statistical_chunking(sample_text, embedding_model=model)
    assert len(chunks) > 0


def test_modality_specific_chunking():
    mixed_doc = (
        "Intro text talking about math animations.\n\n"
        "```python\n"
        "def animate_circle(scene):\n"
        "    circle = Circle()\n"
        "    scene.play(Create(circle))\n"
        "```\n\n"
        "Outro text after code block."
    )
    chunks = modality_specific_chunking(mixed_doc)
    assert len(chunks) >= 2
    assert any(c["metadata"].get("modality") == "code" for c in chunks)
    assert any(c["metadata"].get("modality") == "text" for c in chunks)


def test_registry_contains_all():
    assert len(CHUNKING_METHODS) == 15
    for name in CHUNKING_METHODS:
        assert callable(CHUNKING_METHODS[name])


def test_autodetect_and_chunk(sample_text: str):
    # Py file autodetection
    py_code = "def process():\n    pass"
    chunks_py = autodetect_and_chunk(py_code, file_path="script.py")
    assert len(chunks_py) > 0
    assert chunks_py[0]["metadata"]["method"] == "document_specific"

    # Md file autodetection
    md_text = "# Header\nContent"
    chunks_md = autodetect_and_chunk(md_text, file_path="doc.md")
    assert len(chunks_md) > 0
    assert chunks_md[0]["metadata"]["method"] == "document_specific"

    # Mixed code blocks
    mixed = "Text\n```python\npass\n```"
    chunks_mixed = autodetect_and_chunk(mixed, file_path="post.txt")
    assert len(chunks_mixed) > 0
    assert any(c["metadata"].get("method") == "modality_specific" for c in chunks_mixed)

    # General prose fallback
    chunks_fallback = autodetect_and_chunk(sample_text, file_path="essay.txt")
    assert len(chunks_fallback) > 0
    assert chunks_fallback[0]["metadata"]["method"] == "recursive"
