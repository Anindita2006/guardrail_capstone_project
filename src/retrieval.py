"""Chunking + vector (embedding) retrieval over the policy corpus, with citation
metadata. Embeddings run locally via sentence-transformers — no API calls, no cost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "policies"

CLAUSE_HEADER_RE = re.compile(r"^###\s+([A-Z]+-\d+)\.\s+(.+)$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Clause:
    doc_id: str
    clause_id: str
    title: str
    owner: str
    source_title: str
    text: str

    @property
    def citation(self) -> str:
        return f"{self.clause_id} ({self.source_title})"


def _parse_frontmatter(raw: str) -> dict:
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm


def load_corpus(corpus_dir: Path = CORPUS_DIR) -> list[Clause]:
    clauses: list[Clause] = []
    for path in sorted(corpus_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(raw)
        body = FRONTMATTER_RE.sub("", raw)
        owner = fm.get("owner", "Compliance Team")
        source_title = fm.get("title", path.stem)

        headers = list(CLAUSE_HEADER_RE.finditer(body))
        for i, m in enumerate(headers):
            clause_id, title = m.group(1), m.group(2).strip()
            start = m.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
            text = body[start:end].strip()
            clauses.append(
                Clause(
                    doc_id=fm.get("doc_id", path.stem.upper()),
                    clause_id=clause_id,
                    title=title,
                    owner=owner,
                    source_title=source_title,
                    text=text,
                )
            )
    return clauses


class PolicyIndex:
    """Sentence-embedding search index over policy clauses (local model, no API calls)."""

    def __init__(self, corpus_dir: Path = CORPUS_DIR):
        self.clauses = load_corpus(corpus_dir)
        if not self.clauses:
            raise RuntimeError(f"No policy clauses found in {corpus_dir}")
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        corpus_texts = [f"{c.title}. {c.text}" for c in self.clauses]
        self.embeddings = self.model.encode(
            corpus_texts, normalize_embeddings=True, convert_to_numpy=True
        )

    def search(self, query: str, k: int = 4) -> list[dict]:
        q_vec = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self.embeddings @ q_vec  # cosine similarity, since both sides are normalized
        ranked = np.argsort(-scores)[:k]
        results = []
        for i in ranked:
            c = self.clauses[i]
            results.append(
                {
                    "clause_id": c.clause_id,
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "owner": c.owner,
                    "source_title": c.source_title,
                    "text": c.text,
                    "citation": c.citation,
                    "score": round(float(scores[i]), 4),
                }
            )
        return results


_index: PolicyIndex | None = None


def get_index() -> PolicyIndex:
    global _index
    if _index is None:
        _index = PolicyIndex()
    return _index
