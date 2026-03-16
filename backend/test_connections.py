"""
Smoke-tests each external dependency used by WanderBot Phase 1.
Run with: uv run python test_connections.py
"""

import sys

PASS = "  PASS"
FAIL = "  FAIL"

def check(label: str, fn):
    try:
        result = fn()
        print(f"{PASS}  {label}" + (f" — {result}" if result else ""))
        return True
    except Exception as e:
        print(f"{FAIL}  {label} — {e}")
        return False

# ── 1. Config ──────────────────────────────────────────────────────────────
print("\n[1] Config")
from src.config import (
    GROQ_API_KEY, TAVILY_API_KEY, HUGGINGFACEHUB_API_TOKEN,
    QDRANT_URL, QDRANT_API_KEY, GROQ_MODEL
)
check("GROQ_API_KEY loaded",            lambda: f"{GROQ_API_KEY[:8]}...")
check("TAVILY_API_KEY loaded",          lambda: f"{TAVILY_API_KEY[:8]}...")
check("HUGGINGFACEHUB_API_TOKEN loaded",lambda: f"{HUGGINGFACEHUB_API_TOKEN[:8]}...")
check("QDRANT_URL loaded",              lambda: QDRANT_URL)
check("QDRANT_API_KEY loaded",          lambda: f"{QDRANT_API_KEY[:8]}...")

# ── 2. Groq LLM ────────────────────────────────────────────────────────────
print("\n[2] Groq LLM")
def test_groq():
    from langchain_groq import ChatGroq
    llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)
    resp = llm.invoke("Say 'ok' and nothing else.")
    return resp.content.strip()[:20]

check(f"Groq ({GROQ_MODEL}) responds", test_groq)

# ── 3. Tavily search ───────────────────────────────────────────────────────
print("\n[3] Tavily")
def test_tavily():
    from langchain_community.tools.tavily_search import TavilySearchResults
    tool = TavilySearchResults(max_results=1)
    results = tool.invoke("Tokyo travel guide")
    return f"{len(results)} result(s)"

check("Tavily returns results", test_tavily)

# ── 4. HuggingFace embeddings ──────────────────────────────────────────────
print("\n[4] HuggingFace Embeddings")
def test_embeddings():
    from langchain_huggingface import HuggingFaceEndpointEmbeddings
    emb = HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        huggingfacehub_api_token=HUGGINGFACEHUB_API_TOKEN,
    )
    vec = emb.embed_query("test")
    return f"dim={len(vec)}"

check("HuggingFace embeds a string (dim=384 expected)", test_embeddings)

# ── 5. Qdrant ──────────────────────────────────────────────────────────────
print("\n[5] Qdrant")
def test_qdrant():
    from qdrant_client import QdrantClient
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    info = client.get_collections()
    return f"{len(info.collections)} collection(s) visible"

check("Qdrant cloud reachable", test_qdrant)

# ── 6. WebBaseLoader scrape ────────────────────────────────────────────────
print("\n[6] Web scraping")
def test_scrape():
    from langchain_community.document_loaders import WebBaseLoader
    loader = WebBaseLoader("https://www.lonelyplanet.com/japan/tokyo")
    docs = loader.load()
    return f"{len(docs)} doc(s), ~{len(docs[0].page_content)} chars"

check("WebBaseLoader scrapes a page", test_scrape)

# ── 7. Graph imports & compiles ────────────────────────────────────────────
print("\n[7] LangGraph")
def test_graph():
    from src.graph import graph
    nodes = [n for n in graph.nodes if not n.startswith("__")]
    return " → ".join(nodes)

check("Graph compiles with all nodes", test_graph)

# ── Summary ────────────────────────────────────────────────────────────────
print("\n" + "─" * 50)
print("All checks done. Fix any FAIL before running the full agent.")
print("Full agent: uv run python src/main.py")
