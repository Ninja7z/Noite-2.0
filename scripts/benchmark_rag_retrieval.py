from __future__ import annotations

import json
import math
import re
import sqlite3
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:11434/api/embed"
MODEL = "nomic-embed-text"
CHUNK_CHARS = 1400
OVERLAP = 220
TOP_K = 5

QUERIES = [
    (
        "Como uma ferramenta é autorizada antes de executar e quem registra a auditoria?",
        "SECURITY_ARCHITECTURE.md",
    ),
    (
        "Quais formatos de arquivos o chat aceita e quais são os limites de tamanho?",
        "ATTACHMENTS.md",
    ),
    (
        "Qual critério precisa ser atingido antes de adotar sqlite-vec e embeddings?",
        "004-memory-storage.md",
    ),
    ("Quais portas e serviços são iniciados pelo script run_noite.ps1?", "MCP_STATUS.md"),
    ("Quando uma tarefa pode ser enviada ao GLM e quais dados são proibidos?", "MODEL_ROUTING.md"),
    (
        "Qual é o fluxo entre AssistantService, Model Gateway, autorização e execução?",
        "SYSTEM_ARCHITECTURE.md",
    ),
    ("Quais eventos e atualizações em tempo real o aplicativo web precisa expor?", "WEB_APP.md"),
    (
        "Como o sistema garante que dados de conversas diferentes não sejam misturados?",
        "MEMORY_ARCHITECTURE.md",
    ),
    ("Como são processados PDFs e documentos Office sem executar o conteúdo?", "ATTACHMENTS.md"),
    ("Como a Noite decide entre modelos locais e o provedor externo?", "MODEL_ROUTING.md"),
]


def embed(inputs: list[str]) -> list[list[float]]:
    payload = json.dumps({"model": MODEL, "input": inputs}).encode()
    request = Request(API, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=180) as response:
        result = json.loads(response.read())
    return result["embeddings"]


def chunks(text: str):
    text = text.replace("\r\n", "\n")
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_CHARS)
        excerpt = text[start:end].strip()
        if len(excerpt) >= 100:
            yield excerpt
        if end == len(text):
            break
        start = end - OVERLAP


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def lexical_top(chunks_data, query):
    terms = [
        t.casefold()
        for t in re.findall(r"[\wÀ-ÿ]{3,}", query)
        if t.casefold() not in {"que", "para", "com", "uma", "qual", "quais"}
    ]
    scored = []
    for i, item in enumerate(chunks_data):
        body = item["text"].casefold()
        score = sum(body.count(term) for term in terms)
        if score:
            scored.append((score, i))
    return [i for _, i in sorted(scored, reverse=True)[:TOP_K]]


def fts_top(connection, query):
    terms = [
        t
        for t in re.findall(r"[\wÀ-ÿ]{3,}", query)
        if t.casefold() not in {"que", "para", "com", "uma", "qual", "quais"}
    ][:20]
    if not terms:
        return []
    match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
    try:
        rows = connection.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, TOP_K),
        ).fetchall()
        return [int(row[0]) - 1 for row in rows]
    except sqlite3.OperationalError:
        return []


def metrics(rankings):
    hits = []
    reciprocal = []
    for ranked, expected in rankings:
        ranks = [
            position + 1 for position, idx in enumerate(ranked) if expected in docs[idx]["name"]
        ]
        hits.append(bool(ranks))
        reciprocal.append(1 / ranks[0] if ranks else 0.0)
    return sum(hits) / len(hits), sum(reciprocal) / len(reciprocal)


docs = []
for path in sorted((ROOT / "docs").rglob("*.md")):
    if "archive" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        continue
    for part in chunks(text):
        docs.append({"name": path.name, "path": str(path.relative_to(ROOT)), "text": part})

if not docs:
    raise SystemExit("Nenhum documento Markdown elegível foi encontrado.")

started = time.perf_counter()
doc_vectors = embed(["search_document: " + item["text"] for item in docs])
embedding_ms = (time.perf_counter() - started) * 1000

connection = sqlite3.connect(":memory:")
connection.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(name, content)")
connection.executemany(
    "INSERT INTO chunks_fts(rowid, name, content) VALUES (?, ?, ?)",
    [(i + 1, item["name"], item["text"]) for i, item in enumerate(docs)],
)

vector_rankings = []
fts_rankings = []
lexical_rankings = []
query_latencies = []
for query, expected in QUERIES:
    started = time.perf_counter()
    query_vector = embed(["search_query: " + query])[0]
    query_latencies.append((time.perf_counter() - started) * 1000)
    vector_top = sorted(
        range(len(docs)), key=lambda i: cosine(query_vector, doc_vectors[i]), reverse=True
    )[:TOP_K]
    vector_rankings.append((vector_top, expected))
    fts_rankings.append((fts_top(connection, query), expected))
    lexical_rankings.append((lexical_top(docs, query), expected))

print(
    json.dumps(
        {
            "model": MODEL,
            "documents": len({item["path"] for item in docs}),
            "chunks": len(docs),
            "queries": len(QUERIES),
            "top_k": TOP_K,
            "embedding_index_ms": round(embedding_ms, 1),
            "query_embedding_ms_p50": round(statistics.median(query_latencies), 1),
            "query_embedding_ms_p95": round(
                sorted(query_latencies)[max(0, math.ceil(len(query_latencies) * 0.95) - 1)], 1
            ),
            "recall_at_5": {
                "nomic_embeddings": round(metrics(vector_rankings)[0], 3),
                "sqlite_fts5": round(metrics(fts_rankings)[0], 3),
                "simple_lexical": round(metrics(lexical_rankings)[0], 3),
            },
            "mrr_at_5": {
                "nomic_embeddings": round(metrics(vector_rankings)[1], 3),
                "sqlite_fts5": round(metrics(fts_rankings)[1], 3),
                "simple_lexical": round(metrics(lexical_rankings)[1], 3),
            },
            "per_query": [
                {
                    "query": query,
                    "expected": expected,
                    "vector_top": [docs[i]["name"] for i in vector_rankings[n][0]],
                    "fts_top": [docs[i]["name"] for i in fts_rankings[n][0]],
                }
                for n, (query, expected) in enumerate(QUERIES)
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
)
