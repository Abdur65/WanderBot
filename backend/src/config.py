import os
from decouple import config

GROQ_API_KEY = config("GROQ_API_KEY")
TAVILY_API_KEY = config("TAVILY_API_KEY")
HUGGINGFACEHUB_API_TOKEN = config("HUGGINGFACEHUB_API_TOKEN")
QDRANT_URL = config("QDRANT_URL", default=None)
QDRANT_API_KEY = config("QDRANT_API_KEY", default=None)
ORS_API_KEY = config("ORS_API_KEY", default=None)

# Expose keys as env vars so LangChain tools that read os.environ directly can find them
os.environ.setdefault("TAVILY_API_KEY", TAVILY_API_KEY)
os.environ.setdefault("GROQ_API_KEY", GROQ_API_KEY)
os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", HUGGINGFACEHUB_API_TOKEN)
os.environ.setdefault("USER_AGENT", "WanderBot/1.0")
if ORS_API_KEY:
    os.environ.setdefault("ORS_API_KEY", ORS_API_KEY)

GROQ_MODEL = "llama-3.3-70b-versatile"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RAG_TOP_K = 5
MAX_RETRIES = 3
MAX_TAVILY_CALLS = 10