"""RAG / Vector retriever for local code intelligence.

Uses LanceDB (local vector DB) + jina-embeddings-v2-base-code (ONNX int8 when possible).
Always provides a zero-dep keyword fallback.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:
    import lancedb
    import numpy as np
    from sentence_transformers import SentenceTransformer
    _HAS_VECTOR_DEPS = True
except ImportError:
    lancedb = None
    np = None
    SentenceTransformer = None
    _HAS_VECTOR_DEPS = False


class KeywordRetriever:
    """Zero-dependency fallback: keyword + section-based retrieval."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace
        self._cache: dict[str, str] = {}  # filename -> content

    def load_files(self, files: list[str]) -> None:
        if not self.workspace:
            return
        for name in files:
            p = self.workspace / name
            if p.exists():
                try:
                    if p.suffix.lower() == ".pdf":
                        import subprocess
                        try:
                            content = subprocess.check_output(["pdftotext", str(p), "-"], text=True, errors="ignore")
                            self._cache[name] = content
                        except Exception:
                            pass
                    else:
                        self._cache[name] = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

    def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self._cache:
            return []

        q = query.lower()
        results = []
        for fname, content in self._cache.items():
            score = 0
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if q in line.lower():
                    score += 10
                    # bonus for section headers
                    if re.search(r"# ---DIV:|---|def |class ", line):
                        score += 5
                    results.append({
                        "file": fname,
                        "chunk": "\n".join(lines[max(0, i-2):i+5]),
                        "score": score,
                        "type": "keyword",
                    })
            # simple term frequency
            score += content.lower().count(q) * 2

        # also search for section titles
        for fname, content in self._cache.items():
            for match in re.finditer(r"# ---DIV:\s*([^-]+)---", content):
                title = match.group(1).strip().lower()
                if any(w in title for w in q.split()):
                    results.append({
                        "file": fname,
                        "chunk": content[match.start():match.end() + 200],
                        "score": 8,
                        "type": "section",
                    })

        results.sort(key=lambda x: -x["score"])
        return results[:top_k]


class VectorRetriever:
    """LanceDB + Jina embeddings based retriever. Lazy initialized."""

    def __init__(self, workspace: Path | None = None, model_dir: Path | None = None):
        self.workspace = workspace
        self.model_dir = model_dir or Path.home() / ".cache" / "matemium" / "models"
        self._model: Any = None
        self._db: Any = None
        self._table = None
        self._initialized = False
        self._use_vector = _HAS_VECTOR_DEPS

    def _load_model(self):
        if self._model is not None:
            return self._model

        if not self._use_vector:
            raise RuntimeError("Vector dependencies not installed (lancedb / sentence-transformers)")

        os.makedirs(self.model_dir, exist_ok=True)

        # Prefer ONNX int8 quantized if available via optimum / onnxruntime
        # For jina-embeddings-v2-base-code, sentence-transformers + trust_remote_code works.
        # To force ONNX: model = SentenceTransformer(..., model_kwargs={"onnx": True}) or use optimum.
        try:
            # This will download if needed. For quantized ONNX, user can pre-convert or use:
            # https://huggingface.co/jinaai/jina-embeddings-v2-base-code
            self._model = SentenceTransformer(
                "jinaai/jina-embeddings-v2-base-code",
                cache_folder=str(self.model_dir),
                trust_remote_code=True,
            )
            # TODO: in future use optimum.onnxruntime for int8
        except Exception as e:
            print(f"[intelligence] Failed to load Jina model, falling back: {e}")
            self._use_vector = False
            raise
        return self._model

    def _get_db(self):
        if not self.workspace:
            return None
        if self._db is not None:
            return self._db
        db_path = self.workspace / ".matemium" / "vectors"
        db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(db_path))
        return self._db

    def _get_table(self, name: str = "code_chunks"):
        if self._table is not None:
            return self._table
        db = self._get_db()
        if db is None:
            return None
        try:
            self._table = db.open_table(name)
        except Exception:
            # Create with schema on first insert
            self._table = None
        return self._table

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        # Jina models produce 768-dim embeddings
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def index_files(self, files: list[str], force: bool = False, events: Any = None) -> int:
        """Index the given files (scenes.py, assets.py, etc.). Returns number of chunks."""
        if not self.workspace or not self._use_vector:
            return 0

        db = self._get_db()
        if db is None:
            return 0

        chunks = []
        for fname in files:
            p = self.workspace / fname
            if not p.exists():
                continue
            try:
                if p.suffix.lower() == ".pdf":
                    import subprocess
                    try:
                        text = subprocess.check_output(["pdftotext", str(p), "-"], text=True, errors="ignore")
                    except Exception:
                        continue
                else:
                    text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            from .chunking import autodetect_and_chunk
            file_chunks = autodetect_and_chunk(text, file_path=p, embedding_model=self._model)
            if file_chunks and events is not None:
                method = file_chunks[0]["metadata"].get("method", "unknown")
                msg = f"Autodetected optimal chunker for {fname}: '{method}' ({len(file_chunks)} chunks)"
                events.emit("loading_phase", phase="CHUNKING_STATUS", message=msg)
            for fc in file_chunks:
                chunks.append({"file": fname, "text": fc["text"]})

        if not chunks:
            return 0

        table = self._get_table()
        if table is None or force:
            # Create table
            data = [
                {
                    "file": c["file"],
                    "text": c["text"][:2000],  # limit chunk size
                    "vector": self.embed([c["text"]])[0],
                }
                for c in chunks
            ]
            if data:
                self._table = db.create_table("code_chunks", data=data, mode="overwrite")
            return len(data)

        # Append mode (simplified - in real use, use upsert or delete old)
        existing = table.to_pandas() if hasattr(table, "to_pandas") else []
        new_chunks = [c for c in chunks if c["text"] not in [e.get("text", "") for e in existing]]
        if new_chunks:
            data = [
                {
                    "file": c["file"],
                    "text": c["text"][:2000],
                    "vector": self.embed([c["text"]])[0],
                }
                for c in new_chunks
            ]
            table.add(data)
        return len(new_chunks)

    def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self._use_vector or not self.workspace:
            return []

        try:
            table = self._get_table()
            if table is None:
                return []

            qvec = self.embed([query])[0]
            results = (
                table.search(qvec)
                .limit(top_k)
                .to_pandas()
            )
            out = []
            for _, row in results.iterrows():
                out.append({
                    "file": row.get("file", ""),
                    "chunk": str(row.get("text", ""))[:1500],
                    "score": float(row.get("_distance", 0.0)),
                    "type": "vector",
                })
            return out
        except Exception as e:
            print(f"[intelligence] Vector retrieve failed: {e}")
            return []


def get_retriever(workspace: Path | None = None, prefer_vector: bool = True) -> Any:
    """Factory: returns VectorRetriever if possible, else KeywordRetriever."""
    if prefer_vector and _HAS_VECTOR_DEPS:
        try:
            return VectorRetriever(workspace=workspace)
        except Exception:
            pass
    return KeywordRetriever(workspace=workspace)
