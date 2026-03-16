from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from src.config import TAVILY_API_KEY, HUGGINGFACEHUB_API_TOKEN, CHUNK_SIZE, CHUNK_OVERLAP, QDRANT_URL, QDRANT_API_KEY
from src.state import AgentState


search = TavilySearchResults(api_key=TAVILY_API_KEY, max_results=5)
splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=HUGGINGFACEHUB_API_TOKEN
)

EMBEDDING_VECTOR_SIZE = 384  # sentence-transformers/all-MiniLM-L6-v2 output dimension

_qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
_vector_stores: dict[str, QdrantVectorStore] = {}

def get_vector_store(destination: str) -> QdrantVectorStore:
    if destination not in _vector_stores:
        collection_name = f"travel_{destination.lower().replace(' ', '_')}"
        _vector_stores[destination] = QdrantVectorStore(
            client=_qdrant_client,
            collection_name=collection_name,
            embedding=embeddings,
            validate_collection_config=False,
        )
    return _vector_stores[destination]

def curate_knowledge(state: AgentState) -> dict:
    destination = state["destination"]

    if state.get("knowledge_ready"):
        print(f"[Curate] Knowledge already indexed for {destination}, skipping.")
        return {}

    print(f"[Curate] Searching for travel blogs about {destination}...")

    results = search.invoke(f"Best travel guide blog {destination} things to do tips")
    new_tavily_calls = state.get("tavily_calls", 0) + 1

    urls = [r["url"] for r in results if "url" in r]
    print(f"[Curate] Found {len(urls)} URLs to scrape.")

    documents = []
    for url in urls[:4]:  # cap at 4 to avoid long waits
        try:
            loader = WebBaseLoader(url)
            docs = loader.load()
            documents.extend(docs)
            print(f"[Curate] Scraped: {url}")
        except Exception as e:
            print(f"[Curate] Failed to scrape {url}: {e}")

    if not documents:
        print("[Curate] No documents scraped — will rely on live search only.")
        return {"knowledge_ready": True, "tavily_calls": new_tavily_calls}

    chunks = splitter.split_documents(documents)
    print(f"[Curate] Split into {len(chunks)} chunks.")

    # Ensure collection exists before writing (Qdrant won't auto-create it)
    collection_name = f"travel_{destination.lower().replace(' ', '_')}"
    if not _qdrant_client.collection_exists(collection_name):
        _qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=EMBEDDING_VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"[Curate] Created Qdrant collection '{collection_name}'.")

    vector_store = get_vector_store(destination)
    vector_store.add_documents(chunks)
    print(f"[Curate] Indexed {len(chunks)} chunks into Qdrant.")

    return {"knowledge_ready": True, "tavily_calls": new_tavily_calls}