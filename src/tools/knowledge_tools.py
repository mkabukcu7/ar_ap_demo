"""Finance knowledge retrieval (RAG) tools.

In `local` mode retrieval is a dependency-free lexical (BM25-style) search over
the markdown policy documents in `sample-data/knowledge`. In `foundry` mode the
same tool contract is served by Azure AI Search using the hybrid + semantic
configuration in `infra/search/index-finance-knowledge.json`.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from src.data.store import FinanceDataStore, get_store

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "our", "over", "that", "the", "to", "we", "what", "when", "which", "who",
    "why", "with", "does", "can", "should",
}

SYNONYMS = {
    "sox": ["sox", "control", "controls", "fin-sox"],
    "approval": ["approval", "approvals", "approve", "authority", "delegation"],
    "approvals": ["approval", "approvals", "approve", "authority", "delegation"],
    "unapplied": ["unapplied", "cash", "application"],
    "duplicate": ["duplicate", "duplicates", "duplicate_suspected"],
    "dso": ["dso", "days", "sales", "outstanding"],
    "vendor": ["vendor", "supplier", "master"],
    "invoice": ["invoice", "invoices", "payable"],
}


def _s(store: FinanceDataStore | None) -> FinanceDataStore:
    return store or get_store()


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9\-]+", text.lower()) if token not in STOP_WORDS]


def _expand(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, [token]))
    return expanded


def search_finance_knowledge(
    query: str,
    top: int = 3,
    document_type: str | None = None,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """Retrieve grounded, citable passages from finance policy documentation."""

    data = _s(store)
    documents = data.knowledge
    if document_type:
        documents = [doc for doc in documents if document_type.lower() in doc["document_id"].lower()]
    if not documents:
        return {"query": query, "results": [], "count": 0}

    query_tokens = _expand(_tokenize(query))
    if not query_tokens:
        return {"query": query, "results": [], "count": 0}

    corpus = [Counter(_tokenize(f"{doc['title']} {doc['section']} {doc['content']}")) for doc in documents]
    doc_count = len(documents)
    doc_freq: Counter[str] = Counter()
    for counts in corpus:
        for term in counts:
            doc_freq[term] += 1

    avg_len = sum(sum(counts.values()) for counts in corpus) / doc_count
    k1, b = 1.5, 0.75

    scored: list[tuple[float, dict[str, Any]]] = []
    for document, counts in zip(documents, corpus):
        length = sum(counts.values()) or 1
        score = 0.0
        for term in query_tokens:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            idf = math.log(1 + (doc_count - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            score += idf * (frequency * (k1 + 1)) / (frequency + k1 * (1 - b + b * length / avg_len))
        if term_in_heading := sum(1 for term in query_tokens if term in _tokenize(document["section"])):
            score *= 1 + 0.15 * term_in_heading
        if score > 0:
            scored.append((score, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = [
        {
            "title": document["title"],
            "section": document["section"],
            "source": document["source"],
            "document_id": document["document_id"],
            "score": round(score, 4),
            "snippet": _snippet(document["content"], query_tokens),
            "content": document["content"],
        }
        for score, document in scored[:top]
    ]
    return {"query": query, "results": results, "count": len(results)}


def _snippet(content: str, query_tokens: list[str], max_chars: int = 480) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    scored_lines = sorted(
        lines,
        key=lambda line: sum(1 for token in query_tokens if token in line.lower()),
        reverse=True,
    )
    best = scored_lines[0] if scored_lines else content
    index = content.find(best)
    start = max(index, 0)
    snippet = content[start : start + max_chars].strip()
    if len(content) > start + max_chars:
        snippet += " …"
    return snippet


def answer_with_citations(
    query: str,
    top: int = 3,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """Compose a grounded answer plus citations for a finance policy question."""

    retrieval = search_finance_knowledge(query, top=top, store=store)
    if not retrieval["results"]:
        return {
            "answer": (
                "I could not find that in the approved finance documentation. "
                "Please raise a request with Finance Systems so the policy can be added."
            ),
            "citations": [],
        }

    top_result = retrieval["results"][0]
    answer_lines = [f"**{top_result['title']} — {top_result['section']}**", "", top_result["snippet"]]
    if len(retrieval["results"]) > 1:
        answer_lines.append("")
        answer_lines.append("Related guidance:")
        for result in retrieval["results"][1:]:
            answer_lines.append(f"- {result['title']} — {result['section']}")

    return {
        "answer": "\n".join(answer_lines),
        "citations": [
            {"title": f"{result['title']} — {result['section']}", "source": result["source"], "snippet": result["snippet"]}
            for result in retrieval["results"]
        ],
        "control": "FIN-SOX-AI-03",
    }
