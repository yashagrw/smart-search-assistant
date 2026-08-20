import logging
import chromadb
import google.generativeai as genai

logger = logging.getLogger(__name__)

class CustomGeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """Custom embedding class bridging Google Gemini's API with ChromaDB."""
    def __init__(self):
        pass

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=input,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']

def query_knowledge_base(search_query: str) -> str:
    """Queries the ChromaDB vector store and returns formatted results."""
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        custom_google_ef = CustomGeminiEmbeddingFunction()
        collection = client.get_collection(name="company_policies", embedding_function=custom_google_ef)
        
        # 2 chunks nikal rahe hain closest meaning wale
        results = collection.query(
            query_texts=[search_query],
            n_results=2 
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant policies found in the knowledge base."
            
        formatted_results = []
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            formatted_results.append(f"[Source: {meta['section']}]\n{doc}")
            
        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"RAG Service Error: {e}")
        return f"Database retrieval error: {str(e)}"