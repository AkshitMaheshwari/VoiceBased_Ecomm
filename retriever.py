"""
Hybrid Retriever: Dense (ChromaDB) + Sparse (BM25) with Reciprocal Rank Fusion.
- Query-level cache to avoid re-embedding identical/similar queries
- Eager warm-up at import time (no cold-start lag on first query)
- Structured context formatting for cleaner LLM input
"""

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi
import os
import hashlib
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"

# ---------------------------------------------------------------------------
# Simple in-process query cache (TTL-based)
# ---------------------------------------------------------------------------
_CACHE: dict = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes



def _cache_key(query: str, filters: dict | None) -> str:
    payload = f"{query.strip().lower()}::{str(filters)}"
    return hashlib.md5(payload.encode()).hexdigest()


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL_SECONDS:
        return entry["docs"]
    return None


def _cache_set(key: str, docs):
    _CACHE[key] = {"docs": docs, "ts": time.time()}


def _build_filters(user_memory) -> dict | None:
    conditions = []

    brand = user_memory.pref.get("brand")
    category = user_memory.pref.get("category")
    budget = user_memory.pref.get("budget")

    if brand:
        title_brand = brand.title()
        conditions.append({"brand": {"$in": [brand, brand.lower(), brand.upper(), title_brand]}})

    if category:
        title_cat = category.title()
        conditions.append({"category": {"$in": [category, category.lower(), category.upper(), title_cat]}})

    if budget:
        conditions.append({"price": {"$lte": budget}})

    if len(conditions) > 1:
        return {"$and": conditions}
    if len(conditions) == 1:
        return conditions[0]
    return None


# ---------------------------------------------------------------------------
# ChromaDB client
# ---------------------------------------------------------------------------

class ChromaClient:
    def __init__(self):
        print("[*] Loading embedding model...", flush=True)
        self.embeddings = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        )
        self.db = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=self.embeddings,
        )
        # Warm-up: embed a dummy query so the model is hot for real queries
        self.embeddings.embed_query("warmup")
        print("[OK] Embedding model ready.", flush=True)

    def dense_search(self, query: str, k: int = 10, filters: dict | None = None):
        if filters:
            return self.db.similarity_search(query, k=k, filter=filters)
        return self.db.similarity_search(query, k=k)

    def get_all_docs(self):
        """Fetch all stored docs for BM25 index construction."""
        result = self.db.get()
        from langchain_core.documents import Document
        docs = []
        for i, doc_id in enumerate(result["ids"]):
            content = result["documents"][i]
            meta = result["metadatas"][i] if result["metadatas"] else {}
            docs.append(Document(page_content=content, metadata=meta))
        return docs


# ---------------------------------------------------------------------------
# Hybrid Retriever (BM25 + Dense + RRF)
# ---------------------------------------------------------------------------

class HybridRetriever:
    def __init__(self, chroma: ChromaClient):
        self.chroma = chroma
        self._build_bm25_index()

    def _build_bm25_index(self):
        print("[*] Building BM25 index...", flush=True)
        self._all_docs = self.chroma.get_all_docs()
        if self._all_docs:
            tokenized = [doc.page_content.lower().split() for doc in self._all_docs]
            self._bm25 = BM25Okapi(tokenized)
            print(f"[OK] BM25 index ready ({len(self._all_docs)} docs).", flush=True)
        else:
            self._bm25 = None
            print("[WARN] No documents found in ChromaDB — BM25 skipped.", flush=True)

    def search(self, query: str, k: int = 3, filters: dict | None = None) -> list:
        # --- Cache check ---
        cache_key = _cache_key(query, filters)
        cached = _cache_get(cache_key)
        if cached is not None:
            print("[CACHE] Hit!", flush=True)
            return cached

        # --- Dense retrieval ---
        dense_docs = self.chroma.dense_search(query, k=k * 3, filters=filters)

        # --- BM25 sparse retrieval (only when no hard filters, for speed) ---
        if self._bm25 and not filters:
            tokens = query.lower().split()
            scores = self._bm25.get_scores(tokens)
            top_indices = scores.argsort()[::-1][: k * 3]
            sparse_docs = [self._all_docs[i] for i in top_indices]
        else:
            sparse_docs = []

        # --- Reciprocal Rank Fusion ---
        merged = self._rrf_merge(dense_docs, sparse_docs, k=k)

        _cache_set(cache_key, merged)
        return merged

    @staticmethod
    def _rrf_merge(dense: list, sparse: list, k: int, rrf_k: int = 60) -> list:
        """Combine dense and sparse results using Reciprocal Rank Fusion."""
        scores: dict[str, float] = {}
        doc_map: dict[str, object] = {}

        for rank, doc in enumerate(dense):
            key = doc.page_content[:80]
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            doc_map[key] = doc

        for rank, doc in enumerate(sparse):
            key = doc.page_content[:80]
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            doc_map[key] = doc

        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [doc_map[key] for key in sorted_keys[:k]]


# ---------------------------------------------------------------------------
# Singleton — initialized once at import time (eager warm-up)
# ---------------------------------------------------------------------------

print("[*] Initializing retrieval engine...", flush=True)
_chroma = ChromaClient()
_retriever = HybridRetriever(_chroma)
print("[OK] Retrieval engine ready.\n", flush=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def retrieve(query: str, user_memory) -> list:
    """
    Hybrid-retrieve products matching query + user preferences.
    """
    filters = _build_filters(user_memory)
    return _retriever.search(query, k=3, filters=filters)


def format_context(docs: list) -> str:
    """
    Format retrieved docs as a clean structured block for the LLM.
    Much better than raw page_content concatenation.
    """
    if not docs:
        return "No relevant products found."

    parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        block = f"[Product {i}]\n"
        # Truncate page_content to avoid blowing up the LLM token limit
        content = doc.page_content
        if len(content) > 300:
            content = content[:300] + "... (truncated)"
        block += content
        if meta:
            extras = []
            for key in ("brand", "category", "price", "rating"):
                if key in meta:
                    extras.append(f"{key.capitalize()}: {meta[key]}")
            if extras:
                block += "\n" + " | ".join(extras)
        parts.append(block)

    return "\n\n".join(parts)
