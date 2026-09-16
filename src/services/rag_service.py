# Override standard sqlite3 with modern pysqlite3 if available (required for ChromaDB on legacy Linux)
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except (ImportError, ModuleNotFoundError):
    pass

import os
import logging
from dotenv import load_dotenv
import chromadb
import google.generativeai as genai

logger = logging.getLogger(__name__)

# 🔑 Load environment variables and configure Gemini SDK for self-contained execution
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class CustomGeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    Custom embedding class bridging Google Gemini's native embedding API with ChromaDB.
    Generates 3072-dimensional vector embeddings for query vectors.
    """
    def __init__(self):
        pass

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=input,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']

def compute_rerank_score(query: str, doc_text: str, metadata: dict) -> float:
    """
    Deterministic cross-scoring function that calculates relevance scores (0.0 to 1.0)
    based on exact term overlap, phrase alignment, and departmental relevance metadata.
    """
    query_terms = set(query.lower().split())
    doc_lower = doc_text.lower()
    
    # 1. Exact Term Overlap Score
    matched_terms = sum(1 for term in query_terms if term in doc_lower)
    term_score = matched_terms / max(len(query_terms), 1)

    # 2. Section and Department Metadata Alignment Boost
    dept_boost = 0.0
    dept = metadata.get("department", "").lower()
    section = metadata.get("section", "").lower()

    for term in query_terms:
        if term in dept:
            dept_boost += 0.2
        if term in section:
            dept_boost += 0.3

    # Combined normalized score (capped at 1.0)
    total_score = min(term_score + dept_boost, 1.0)
    return round(total_score, 4)

def query_knowledge_base(search_query: str) -> str:
    """
    Two-Stage Retrieval Engine:
    Stage 1: Broad candidate retrieval (Top-8 from ChromaDB).
    Stage 2: Cross-scoring re-ranking to return the Top-2 highest precision chunks.
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        chroma_path = os.path.join(base_dir, "chroma_db")
        
        client = chromadb.PersistentClient(path=chroma_path)
        custom_google_ef = CustomGeminiEmbeddingFunction()
        collection = client.get_collection(name="company_policies", embedding_function=custom_google_ef)
        
        # --- STAGE 1: BROAD CANDIDATE RETRIEVAL (Top-8 Candidates) ---
        stage1_results = collection.query(
            query_texts=[search_query],
            n_results=8
        )
        
        if not stage1_results['documents'] or not stage1_results['documents'][0]:
            return "No relevant policies found in the knowledge base."
            
        candidate_docs = stage1_results['documents'][0]
        candidate_metas = stage1_results['metadatas'][0]

        # --- STAGE 2: PRECISION RE-RANKING ---
        scored_candidates = []
        for doc, meta in zip(candidate_docs, candidate_metas):
            score = compute_rerank_score(search_query, doc, meta)
            scored_candidates.append({
                "doc": doc,
                "meta": meta,
                "score": score
            })

        # Sort candidates descending by re-rank relevance score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        # Select Top-2 winning chunks
        top_winners = scored_candidates[:2]
        
        logger.info(f"Re-ranker evaluated {len(candidate_docs)} candidates. Winning score: {top_winners[0]['score']}")

        # Format retrieved context with rich metadata tags
        formatted_results = []
        for item in top_winners:
            doc = item["doc"]
            meta = item["meta"]
            score = item["score"]
            formatted_results.append(
                f"[Source: {meta.get('source_file', 'policy.txt')} | Dept: {meta.get('department', 'General')} | Section: {meta.get('section', 'General')} | Relevance: {score}]\n{doc}"
            )
            
        return "\n\n---\n\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"RAG Two-Stage Retrieval Error: {e}", exc_info=True)
        return f"Database retrieval error: {str(e)}"