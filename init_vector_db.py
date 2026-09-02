import os
import re
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CUSTOM EMBEDDING FUNCTION ---
class CustomGeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    A custom embedding class bridging Google Gemini's native embedding API with ChromaDB.
    Bypasses version conflicts and header issues in the default integration.
    """
    def __init__(self):
        # Explicit initialization complying with ChromaDB Base class requirements
        pass

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        """
        Takes a list of string chunks, calls Google Gemini API, and returns a list of embeddings.
        """
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=input,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']

def setup_vector_database():
    """
    Initializes a persistent ChromaDB instance, uses Gemini Embeddings (3072 dimensions), 
    processes unstructured text documents, applies chunking with overlap, 
    extracts metadata, and conditionally upserts embeddings if the database is uninitialized.
    """
    print("🚀 Initializing Enterprise-Grade Vector Database Setup with Gemini Embeddings...")

    # 1. ENVIRONMENT & API CONFIGURATION
    load_dotenv()
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        return

    # Configure native Gemini SDK
    genai.configure(api_key=gemini_api_key)

    # Instantiate custom embedding function
    custom_google_ef = CustomGeminiEmbeddingFunction()

    # 2. PERSISTENT VECTOR STORE CONFIGURATION
    client = chromadb.PersistentClient(path="./chroma_db")
    
    collection = client.get_or_create_collection(
        name="company_policies",
        embedding_function=custom_google_ef
    )

    # Idempotency check: Skip embedding generation if vector store is already populated to optimize cold-start latency
    existing_count = collection.count()
    if existing_count > 0:
        print(f"⚡ Vector database already contains {existing_count} indexed records. Skipping embedding generation.")
        return
    
    file_path = "knowledge_base/company_policies.txt"
    if not os.path.exists(file_path):
        print(f"❌ Error: Knowledge base file not found at {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 3. CHUNKING STRATEGY (WITH OVERLAP)
    print("🔪 Processing document using RecursiveCharacterTextSplitter...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", ". ", " "] 
    )

    # 4. METADATA EXTRACTION & STRUCTURAL PARSING
    sections = full_text.split("[SECTION ")
    
    documents = []
    metadatas = []
    ids = []
    chunk_counter = 0

    for section in sections:
        if not section.strip() or "COMPANY OPERATIONS" in section:
            continue
            
        # Extract Section Header (e.g., "1: ORDER CANCELLATIONS")
        section_title_match = re.match(r"(.*?)]", section)
        if section_title_match:
            section_name = section_title_match.group(1).strip()
            section_body = section.replace(section_title_match.group(0), "").strip()
        else:
            section_name = "General"
            section_body = section.strip()

        chunks = text_splitter.split_text(section_body)
        
        for chunk in chunks:
            documents.append(chunk)
            metadatas.append({
                "source": "company_policies.txt",
                "version": "v2.4",
                "section": section_name,
                "chunk_size": len(chunk)
            })
            
            safe_section_name = section_name.split(':')[0].strip().replace(" ", "_")
            ids.append(f"doc_{safe_section_name}_chunk_{chunk_counter}")
            chunk_counter += 1

    print(f"\n📚 Successfully generated {len(documents)} context-aware text chunks.")
    print("Initiating 3072-Dimensional Gemini embedding generation and Vector DB ingestion...")

    # 5. UPSERT OPERATION
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print("\n✅ Operation Successful: Vector Database Populated with Gemini Vectors.")
    print(f"-> Total indexed records in database: {collection.count()}")

if __name__ == "__main__":
    setup_vector_database()