"""Comprehensive chunking strategies for Retrieval-Augmented Generation (RAG).

Implements the top 15 chunking techniques for RAG systems:
1. Fixed-Size Chunking
2. Recursive Character Text Splitting
3. Semantic Chunking
4. Document-Specific Chunking
5. Hierarchical Chunking
6. Sentence-Aware Chunking
7. Token-Based Chunking
8. Sliding Window Chunking
9. Topic-Based Chunking
10. Proposition-Based Chunking
11. Context-Aware Chunking
12. Agentic Chunking
13. Small-to-Big Chunking
14. Statistical Chunking
15. Modality-Specific Chunking

Provides a central registry and smart automatic selection.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Optional dependencies
try:
    import numpy as np
except ImportError:
    np = None


def sentence_tokenize(text: str) -> list[dict[str, Any]]:
    """Splits text into sentences and returns a list of dicts with text, start, and end offsets.
    
    Uses standard punctuation-aware regex to ensure decimal and abbreviation safety.
    """
    sentence_end = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s')
    
    sentences = []
    splits = [0]
    for match in sentence_end.finditer(text):
        splits.append(match.end())
    splits.append(len(text))

    for i in range(len(splits) - 1):
        s_start = splits[i]
        s_end = splits[i+1]
        s_text = text[s_start:s_end].strip()
        if s_text:
            sentences.append({
                "text": s_text,
                "start": s_start,
                "end": s_end
            })
    return sentences


# 1. Fixed-Size Chunking
def fixed_size_chunking(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict[str, Any]]:
    """Divides text into uniform segments based on a predetermined character count with overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        overlap = chunk_size - 1

    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(text), step):
        chunk_text = text[i:i + chunk_size]
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "start_char": i,
                    "end_char": i + len(chunk_text),
                    "method": "fixed_size"
                }
            })
    return chunks


# 2. Recursive Character Text Splitting
def recursive_character_chunking(
    text: str, 
    chunk_size: int = 500, 
    overlap: int = 50, 
    separators: list[str] | None = None
) -> list[dict[str, Any]]:
    """Recursively splits text using a hierarchy of separators to maintain paragraph/sentence structures."""
    if separators is None:
        separators = ["\n\n", "\n", " ", ""]
    
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        overlap = chunk_size - 1

    def split_recursive(txt: str, current_seps: list[str], start_offset: int = 0) -> list[dict[str, Any]]:
        if len(txt) <= chunk_size:
            return [{
                "text": txt,
                "metadata": {"start_char": start_offset, "end_char": start_offset + len(txt), "method": "recursive"}
            }]

        if not current_seps:
            # Fallback: Fixed size chunking
            res = []
            step = chunk_size - overlap
            for i in range(0, len(txt), step):
                chunk_txt = txt[i:i + chunk_size]
                if chunk_txt.strip():
                    res.append({
                        "text": chunk_txt,
                        "metadata": {
                            "start_char": start_offset + i,
                            "end_char": start_offset + i + len(chunk_txt),
                            "method": "recursive"
                        }
                    })
            return res

        sep = current_seps[0]
        next_seps = current_seps[1:]

        parts = list(txt) if sep == "" else txt.split(sep)

        chunks = []
        current_chunk = ""
        current_start = 0

        for i, part in enumerate(parts):
            part_with_sep = part + sep if i < len(parts) - 1 and sep != "" else part
            
            if len(part_with_sep) > chunk_size:
                # Flush the current chunk
                if current_chunk:
                    chunks.append({
                        "text": current_chunk,
                        "metadata": {
                            "start_char": start_offset + current_start,
                            "end_char": start_offset + current_start + len(current_chunk),
                            "method": "recursive"
                        }
                    })
                    current_chunk = ""
                
                # Split oversized segment recursively
                sub_chunks = split_recursive(part_with_sep, next_seps, start_offset + txt.find(part_with_sep))
                chunks.extend(sub_chunks)
                continue

            if len(current_chunk) + len(part_with_sep) <= chunk_size:
                if not current_chunk:
                    current_start = txt.find(part_with_sep)
                current_chunk += part_with_sep
            else:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk,
                        "metadata": {
                            "start_char": start_offset + current_start,
                            "end_char": start_offset + current_start + len(current_chunk),
                            "method": "recursive"
                        }
                    })
                
                overlap_text = current_chunk[-overlap:] if len(current_chunk) >= overlap else current_chunk
                current_chunk = overlap_text + part_with_sep
                current_start = max(0, txt.find(part_with_sep) - len(overlap_text))

        if current_chunk.strip():
            chunks.append({
                "text": current_chunk,
                "metadata": {
                    "start_char": start_offset + current_start,
                    "end_char": start_offset + current_start + len(current_chunk),
                    "method": "recursive"
                }
            })

        return chunks

    return split_recursive(text, separators)


# 3. Semantic Chunking
def semantic_chunking(
    text: str, 
    breakpoint_threshold_type: str = "percentile", 
    breakpoint_threshold_amount: float = 75.0,
    embedding_model: Any = None
) -> list[dict[str, Any]]:
    """Divides text based on semantic similarity transitions using embeddings."""
    sentences = sentence_tokenize(text)
    if not sentences:
        return []

    if len(sentences) == 1:
        return [{
            "text": sentences[0]["text"],
            "metadata": {"start_char": 0, "end_char": len(text), "method": "semantic"}
        }]

    embeddings = None
    if embedding_model is not None:
        try:
            embeddings = embedding_model.encode([s["text"] for s in sentences], convert_to_numpy=True)
        except Exception:
            pass

    if embeddings is None or np is None:
        # Zero-dep fallback
        return sentence_aware_chunking(text, max_chunk_size=500)

    # Calculate cosine similarity between adjacent sentences
    similarities = []
    for i in range(len(embeddings) - 1):
        vec1 = embeddings[i]
        vec2 = embeddings[i+1]
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        sim = np.dot(vec1, vec2) / (norm_product + 1e-9)
        similarities.append(sim)

    # Determine split threshold
    if breakpoint_threshold_type == "percentile":
        threshold = np.percentile(similarities, 100.0 - breakpoint_threshold_amount)
    elif breakpoint_threshold_type == "standard_deviation":
        mean = np.mean(similarities)
        std = np.std(similarities)
        threshold = mean - (breakpoint_threshold_amount / 100.0) * std
    else: # interquartile
        q75, q25 = np.percentile(similarities, [75, 25])
        iqr = q75 - q25
        threshold = q25 - (breakpoint_threshold_amount / 100.0) * iqr

    chunks = []
    current_chunk_sentences = [sentences[0]]
    
    for i, sim in enumerate(similarities):
        next_sentence = sentences[i+1]
        if sim < threshold:
            chunk_text = " ".join([s["text"] for s in current_chunk_sentences])
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "start_char": current_chunk_sentences[0]["start"],
                    "end_char": current_chunk_sentences[-1]["end"],
                    "method": "semantic",
                    "similarity_score": float(sim)
                }
            })
            current_chunk_sentences = [next_sentence]
        else:
            current_chunk_sentences.append(next_sentence)

    if current_chunk_sentences:
        chunk_text = " ".join([s["text"] for s in current_chunk_sentences])
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "start_char": current_chunk_sentences[0]["start"],
                "end_char": current_chunk_sentences[-1]["end"],
                "method": "semantic"
            }
        })

    return chunks


# 4. Document-Specific Chunking
def document_specific_chunking(text: str, file_type: str = "text") -> list[dict[str, Any]]:
    """Leverages syntactic boundaries within files (e.g., Python code or Markdown headers)."""
    chunks = []
    
    if file_type == "python":
        pattern = re.compile(r"(?m)^(# ---DIV:.*---|^def |^class )")
        parts = pattern.split(text)
        
        current_chunk = ""
        current_start = 0
        current_header = ""
        
        for part in parts:
            if pattern.match(part):
                if current_chunk.strip():
                    chunks.append({
                        "text": current_chunk.strip(),
                        "metadata": {
                            "start_char": current_start,
                            "end_char": current_start + len(current_chunk),
                            "method": "document_specific",
                            "header": current_header
                        }
                    })
                current_start = text.find(part)
                current_chunk = part
                current_header = part.strip()
            else:
                current_chunk += part
                
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    "start_char": current_start,
                    "end_char": current_start + len(current_chunk),
                    "method": "document_specific",
                    "header": current_header
                }
            })
            
    elif file_type == "markdown":
        pattern = re.compile(r"(?m)^(#+\s+.*)$")
        parts = pattern.split(text)
        
        current_chunk = ""
        current_start = 0
        current_header = ""
        
        for part in parts:
            if pattern.match(part):
                if current_chunk.strip():
                    chunks.append({
                        "text": current_chunk.strip(),
                        "metadata": {
                            "start_char": current_start,
                            "end_char": current_start + len(current_chunk),
                            "method": "document_specific",
                            "header": current_header
                        }
                    })
                current_start = text.find(part)
                current_chunk = part
                current_header = part.strip()
            else:
                current_chunk += part
                
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    "start_char": current_start,
                    "end_char": current_start + len(current_chunk),
                    "method": "document_specific",
                    "header": current_header
                }
            })
            
    else:
        chunks = recursive_character_chunking(text, chunk_size=500, overlap=50)
        
    return chunks


# 5. Hierarchical Chunking
def hierarchical_chunking(
    text: str, 
    parent_chunk_size: int = 2000, 
    child_chunk_size: int = 400, 
    overlap: int = 50
) -> list[dict[str, Any]]:
    """Creates dual-level chunks, tracking hierarchical mapping from children to parent context."""
    parents = recursive_character_chunking(text, chunk_size=parent_chunk_size, overlap=overlap)
    
    hierarchical_chunks = []
    for parent_idx, parent in enumerate(parents):
        parent_text = parent["text"]
        parent_meta = parent["metadata"]
        
        children = recursive_character_chunking(
            parent_text, 
            chunk_size=child_chunk_size, 
            overlap=overlap
        )
        
        for child_idx, child in enumerate(children):
            child_text = child["text"]
            child_meta = child["metadata"]
            
            abs_start = parent_meta["start_char"] + child_meta["start_char"]
            abs_end = parent_meta["start_char"] + child_meta["end_char"]
            
            hierarchical_chunks.append({
                "text": child_text,
                "metadata": {
                    "start_char": abs_start,
                    "end_char": abs_end,
                    "method": "hierarchical",
                    "parent_index": parent_idx,
                    "child_index": child_idx,
                    "parent_text": parent_text,
                    "parent_start": parent_meta["start_char"],
                    "parent_end": parent_meta["end_char"]
                }
            })
            
    return hierarchical_chunks


# 6. Sentence-Aware Chunking
def sentence_aware_chunking(
    text: str, 
    max_chunk_size: int = 500, 
    overlap_sentences: int = 1
) -> list[dict[str, Any]]:
    """Aggregates whole sentences into chunks, preserving syntactic integrity."""
    sentences = sentence_tokenize(text)
    if not sentences:
        return []
        
    chunks = []
    current_sentences = []
    current_size = 0
    
    for s in sentences:
        sentence_text = s["text"]
        sentence_len = len(sentence_text)
        
        if not current_sentences:
            current_sentences.append(s)
            current_size = sentence_len
        elif current_size + 1 + sentence_len <= max_chunk_size:
            current_sentences.append(s)
            current_size += 1 + sentence_len
        else:
            chunk_text = " ".join([sent["text"] for sent in current_sentences])
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "start_char": current_sentences[0]["start"],
                    "end_char": current_sentences[-1]["end"],
                    "method": "sentence_aware"
                }
            })
            
            if overlap_sentences > 0:
                current_sentences = current_sentences[-overlap_sentences:] + [s]
            else:
                current_sentences = [s]
            current_size = sum(len(sent["text"]) for sent in current_sentences) + len(current_sentences) - 1
            
    if current_sentences:
        chunk_text = " ".join([sent["text"] for sent in current_sentences])
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "start_char": current_sentences[0]["start"],
                "end_char": current_sentences[-1]["end"],
                "method": "sentence_aware"
            }
        })
        
    return chunks


# 7. Token-Based Chunking
def token_based_chunking(
    text: str, 
    chunk_size_tokens: int = 100, 
    overlap_tokens: int = 20, 
    encoding_name: str = "cl100k_base"
) -> list[dict[str, Any]]:
    """Splits text according to strict token bounds using tiktoken (with an approximate fallback)."""
    try:
        import tiktoken
        tokenizer = tiktoken.get_encoding(encoding_name)
        tokens = tokenizer.encode(text)
        
        chunks = []
        step = chunk_size_tokens - overlap_tokens
        if step <= 0:
            step = 1
            
        for i in range(0, len(tokens), step):
            chunk_tokens = tokens[i:i + chunk_size_tokens]
            chunk_text = tokenizer.decode(chunk_tokens)
            
            start_char = text.find(chunk_text[:30]) if len(chunk_text) >= 30 else text.find(chunk_text)
            if start_char == -1:
                start_char = int((i / len(tokens)) * len(text))
            end_char = start_char + len(chunk_text)
            
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "start_char": start_char,
                    "end_char": end_char,
                    "method": "token_based",
                    "token_count": len(chunk_tokens)
                }
            })
        return chunks
    except ImportError:
        # Approximate words split fallback
        words = text.split(" ")
        chunks = []
        step = chunk_size_tokens - overlap_tokens
        if step <= 0:
            step = 1
            
        word_chunk_size = int(chunk_size_tokens * 1.3)
        word_overlap = int(overlap_tokens * 1.3)
        word_step = word_chunk_size - word_overlap
        
        for i in range(0, len(words), word_step):
            chunk_words = words[i:i + word_chunk_size]
            chunk_text = " ".join(chunk_words)
            
            start_char = text.find(chunk_text[:30]) if len(chunk_text) >= 30 else text.find(chunk_text)
            if start_char == -1:
                start_char = int((i / len(words)) * len(text))
            end_char = start_char + len(chunk_text)
            
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "start_char": start_char,
                    "end_char": end_char,
                    "method": "token_based_fallback",
                    "word_count": len(chunk_words)
                }
            })
        return chunks


# 8. Sliding Window Chunking
def sliding_window_chunking(
    text: str, 
    window_size: int = 500, 
    step_size: int = 400
) -> list[dict[str, Any]]:
    """Creates overlapping segments by shifting a fixed window of characters."""
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    if step_size <= 0:
        raise ValueError("step_size must be positive")
        
    chunks = []
    for i in range(0, len(text), step_size):
        chunk_text = text[i:i + window_size]
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "start_char": i,
                    "end_char": i + len(chunk_text),
                    "method": "sliding_window"
                }
            })
            if len(chunk_text) < window_size:
                break
    return chunks


# 9. Topic-Based Chunking
def topic_based_chunking(
    text: str, 
    n_topics: int | None = None, 
    embedding_model: Any = None
) -> list[dict[str, Any]]:
    """Segments and clusters content chronologically based on thematic topics."""
    sentences = sentence_tokenize(text)
    if not sentences:
        return []
        
    if len(sentences) == 1:
        return [{
            "text": sentences[0]["text"],
            "metadata": {"start_char": 0, "end_char": len(text), "method": "topic_based"}
        }]
        
    embeddings = None
    if embedding_model is not None:
        try:
            embeddings = embedding_model.encode([s["text"] for s in sentences], convert_to_numpy=True)
        except Exception:
            pass
            
    if embeddings is None or np is None:
        return semantic_chunking(text, breakpoint_threshold_type="percentile", breakpoint_threshold_amount=50.0)
        
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        return semantic_chunking(text, breakpoint_threshold_type="percentile", breakpoint_threshold_amount=70.0, embedding_model=embedding_model)
        
    if n_topics is None:
        n_topics = max(2, min(len(sentences) // 4, 10))
    if n_topics >= len(sentences):
        n_topics = len(sentences) - 1
        
    kmeans = KMeans(n_clusters=n_topics, random_state=42, n_init="auto")
    topic_labels = kmeans.fit_predict(embeddings)
    
    grouped_sentences: dict[int, list[dict[str, Any]]] = {}
    for i, label in enumerate(topic_labels):
        if label not in grouped_sentences:
            grouped_sentences[label] = []
        grouped_sentences[label].append(sentences[i])
        
    chunks = []
    for label, group in grouped_sentences.items():
        group.sort(key=lambda s: s["start"])
        chunk_text = " ".join([s["text"] for s in group])
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "start_char": group[0]["start"],
                "end_char": group[-1]["end"],
                "method": "topic_based",
                "topic_id": int(label)
            }
        })
    return chunks


# 10. Proposition-Based Chunking
def proposition_based_chunking(
    text: str, 
    llm_client: Any = None
) -> list[dict[str, Any]]:
    """Extracts standalone logical/factual propositions and bundles them."""
    if llm_client is not None:
        try:
            prompt = (
                "Analyze the following text and break it down into separate, independent "
                "logical assertions or factual propositions. Each assertion should be a standalone "
                "sentence that makes a single complete point. Return them as a bulleted list starting with '- ':\n\n"
                f"{text}"
            )
            response = llm_client.complete(prompt)
            lines = response.strip().split("\n")
            propositions = [line.lstrip("- ").strip() for line in lines if line.strip().startswith("-")]
            if propositions:
                chunks = []
                current_prop = []
                current_len = 0
                for prop in propositions:
                    if not current_prop:
                        current_prop.append(prop)
                        current_len = len(prop)
                    elif current_len + len(prop) < 400:
                        current_prop.append(prop)
                        current_len += len(prop)
                    else:
                        chunks.append({
                            "text": " ".join(current_prop),
                            "metadata": {"method": "proposition_based", "propositions": list(current_prop)}
                        })
                        current_prop = [prop]
                        current_len = len(prop)
                if current_prop:
                    chunks.append({
                        "text": " ".join(current_prop),
                        "metadata": {"method": "proposition_based", "propositions": list(current_prop)}
                    })
                return chunks
        except Exception:
            pass

    # Clause / punctuation rule fallback
    sentences = sentence_tokenize(text)
    chunks = []
    for s in sentences:
        clause_splits = re.split(r",\s*(?:and|but|or|for|so|yet)\s+|;\s*", s["text"])
        clauses = [c.strip() for c in clause_splits if c.strip()]
        
        grouped_clauses = []
        current = ""
        for c in clauses:
            if not current:
                current = c
            elif len(current) + len(c) < 150:
                current += ", " + c
            else:
                grouped_clauses.append(current)
                current = c
        if current:
            grouped_clauses.append(current)
            
        for gc in grouped_clauses:
            chunks.append({
                "text": gc,
                "metadata": {
                    "start_char": s["start"] + s["text"].find(gc[:20]) if len(gc) >= 20 else s["start"],
                    "end_char": s["start"] + s["text"].find(gc[-20:]) + 20 if len(gc) >= 20 else s["end"],
                    "method": "proposition_based_fallback",
                    "sentence_parent": s["text"]
                }
            })
    return chunks


# 11. Context-Aware Chunking
def context_aware_chunking(
    text: str, 
    context_window: int = 200, 
    embedding_model: Any = None
) -> list[dict[str, Any]]:
    """Splits text by evaluating context similarity before and after each candidate boundary."""
    sentences = sentence_tokenize(text)
    if not sentences:
        return []
        
    if len(sentences) <= 2:
        return [{
            "text": text,
            "metadata": {"start_char": 0, "end_char": len(text), "method": "context_aware"}
        }]
        
    embeddings = None
    if embedding_model is not None:
        try:
            embeddings = embedding_model.encode([s["text"] for s in sentences], convert_to_numpy=True)
        except Exception:
            pass
            
    if embeddings is None or np is None:
        return recursive_character_chunking(text, chunk_size=500, overlap=50)
        
    context_shifts = []
    for i in range(1, len(sentences) - 1):
        ctx_before_vecs = embeddings[max(0, i-2):i+1]
        ctx_after_vecs = embeddings[i+1:min(len(sentences), i+3)]
        
        mean_before = np.mean(ctx_before_vecs, axis=0)
        mean_after = np.mean(ctx_after_vecs, axis=0)
        
        norm_product = np.linalg.norm(mean_before) * np.linalg.norm(mean_after)
        sim = np.dot(mean_before, mean_after) / (norm_product + 1e-9)
        context_shifts.append((i, sim))
        
    context_shifts.sort(key=lambda x: x[1])
    split_indices = {idx for idx, sim in context_shifts[:max(1, len(context_shifts) // 5)]}
    
    chunks = []
    current_sentences = [sentences[0]]
    for i in range(len(sentences) - 1):
        next_sentence = sentences[i+1]
        if i in split_indices:
            chunk_text = " ".join([s["text"] for s in current_sentences])
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "start_char": current_sentences[0]["start"],
                    "end_char": current_sentences[-1]["end"],
                    "method": "context_aware"
                }
            })
            current_sentences = [next_sentence]
        else:
            current_sentences.append(next_sentence)
            
    if current_sentences:
        chunk_text = " ".join([s["text"] for s in current_sentences])
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "start_char": current_sentences[0]["start"],
                "end_char": current_sentences[-1]["end"],
                "method": "context_aware"
            }
        })
    return chunks


# 12. Agentic Chunking
def agentic_chunking(text: str, llm_client: Any = None) -> list[dict[str, Any]]:
    """Employs an LLM to split a document at highly organic and semantically complete boundaries."""
    if llm_client is not None:
        try:
            prompt = (
                "Analyze the following text and determine optimal chunk boundaries. "
                "Split the text into semantically coherent, complete sections that represent single ideas. "
                "Return the exact text sections separated by the boundary marker '---CHUNK---'. "
                "Do not modify or skip any of the original words.\n\n"
                f"Text:\n{text}"
            )
            response = llm_client.complete(prompt)
            parts = response.split("---CHUNK---")
            chunks = []
            for part in parts:
                p_clean = part.strip()
                if p_clean:
                    start_char = text.find(p_clean[:30]) if len(p_clean) >= 30 else text.find(p_clean)
                    if start_char == -1:
                        start_char = 0
                    chunks.append({
                        "text": p_clean,
                        "metadata": {
                            "start_char": start_char,
                            "end_char": start_char + len(p_clean),
                            "method": "agentic"
                        }
                    })
            if chunks:
                return chunks
        except Exception:
            pass
            
    return recursive_character_chunking(text, chunk_size=500, overlap=50)


# 13. Small-to-Big Chunking
def small_to_big_chunking(
    text: str, 
    child_size: int = 150, 
    parent_size: int = 800
) -> list[dict[str, Any]]:
    """Retains a micro-chunk for precise retrieval and links it to a wider parent context."""
    children = recursive_character_chunking(text, chunk_size=child_size, overlap=20)
    
    chunks = []
    for child in children:
        child_text = child["text"]
        child_meta = child["metadata"]
        
        start_pos = max(0, child_meta["start_char"] - (parent_size - len(child_text)) // 2)
        end_pos = min(len(text), start_pos + parent_size)
        parent_text = text[start_pos:end_pos].strip()
        
        chunks.append({
            "text": child_text,
            "metadata": {
                "start_char": child_meta["start_char"],
                "end_char": child_meta["end_char"],
                "method": "small_to_big",
                "parent_context": parent_text,
                "parent_start": start_pos,
                "parent_end": end_pos
            }
        })
    return chunks


# 14. Statistical Chunking
def statistical_chunking(
    text: str, 
    threshold_percentile: float = 75.0, 
    embedding_model: Any = None
) -> list[dict[str, Any]]:
    """Performs statistical percentile threshold splitting on semantic sentence embeddings."""
    return semantic_chunking(
        text, 
        breakpoint_threshold_type="percentile", 
        breakpoint_threshold_amount=threshold_percentile, 
        embedding_model=embedding_model
    )


# 15. Modality-Specific Chunking
def modality_specific_chunking(text: str, embedding_model: Any = None) -> list[dict[str, Any]]:
    """Routes different blocks (code, standard prose, structural layout) to specialized sub-chunkers."""
    pattern = re.compile(r"(```[a-zA-Z]*\n[\s\S]*?\n```)")
    parts = pattern.split(text)
    
    chunks = []
    current_char = 0
    
    for part in parts:
        if part.startswith("```"):
            code_lines = part.strip().split("\n")
            lang = code_lines[0].replace("```", "").strip()
            code_text = "\n".join(code_lines[1:-1]) if len(code_lines) > 2 else ""
            
            if code_text.strip():
                sub_chunks = document_specific_chunking(code_text, file_type="python" if lang == "python" else "text")
                for sc in sub_chunks:
                    chunks.append({
                        "text": sc["text"],
                        "metadata": {
                            "start_char": current_char + part.find(sc["text"]),
                            "end_char": current_char + part.find(sc["text"]) + len(sc["text"]),
                            "method": "modality_specific",
                            "modality": "code",
                            "language": lang
                        }
                    })
        else:
            if part.strip():
                sub_chunks = sentence_aware_chunking(part, max_chunk_size=500)
                for sc in sub_chunks:
                    chunks.append({
                        "text": sc["text"],
                        "metadata": {
                            "start_char": current_char + part.find(sc["text"]),
                            "end_char": current_char + part.find(sc["text"]) + len(sc["text"]),
                            "method": "modality_specific",
                            "modality": "text"
                        }
                    })
        current_char += len(part)
        
    return chunks


# Central Registry of Chunking Methods
CHUNKING_METHODS = {
    "fixed_size": fixed_size_chunking,
    "recursive_character": recursive_character_chunking,
    "semantic": semantic_chunking,
    "document_specific": document_specific_chunking,
    "hierarchical": hierarchical_chunking,
    "sentence_aware": sentence_aware_chunking,
    "token_based": token_based_chunking,
    "sliding_window": sliding_window_chunking,
    "topic_based": topic_based_chunking,
    "proposition_based": proposition_based_chunking,
    "context_aware": context_aware_chunking,
    "agentic": agentic_chunking,
    "small_to_big": small_to_big_chunking,
    "statistical": statistical_chunking,
    "modality_specific": modality_specific_chunking,
}


def autodetect_and_chunk(
    text: str, 
    file_path: str | Path | None = None, 
    embedding_model: Any = None, 
    llm_client: Any = None
) -> list[dict[str, Any]]:
    """Analyzes text properties (length, file type, syntax) to automatically select and run the optimal chunking strategy."""
    if not text.strip():
        return []

    file_type = "text"
    if file_path:
        ext = Path(file_path).suffix.lower()
        if ext == ".py":
            file_type = "python"
        elif ext in (".md", ".markdown"):
            file_type = "markdown"
        elif ext in (".json", ".js", ".ts", ".html", ".css"):
            file_type = "code"

    # Auto-selection heuristic
    if file_type == "python":
        return document_specific_chunking(text, file_type="python")
    elif file_type == "markdown":
        return document_specific_chunking(text, file_type="markdown")
    elif "```" in text:
        return modality_specific_chunking(text, embedding_model=embedding_model)
    elif embedding_model is not None:
        if len(text) > 5000:
            return hierarchical_chunking(text, parent_chunk_size=2000, child_chunk_size=400)
        else:
            return semantic_chunking(text, embedding_model=embedding_model)
    else:
        # High quality recursive prose chunker
        return recursive_character_chunking(text, chunk_size=500, overlap=50)
