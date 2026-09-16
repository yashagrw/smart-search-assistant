# Override standard sqlite3 with pysqlite3 if available (required for ChromaDB on legacy Linux)
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except (ImportError, ModuleNotFoundError):
    pass

import os
import re
import glob
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CUSTOM EMBEDDING FUNCTION ---
class CustomGeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    Custom embedding class bridging Google Gemini's native embedding API with ChromaDB.
    Generates 3072-dimensional vector embeddings for text chunks.
    """
    def __init__(self):
        pass

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        """
        Processes a list of text chunks, calls Gemini API, and returns 3072-dim embeddings.
        """
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=input,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']

def setup_vector_database():
    """
    Scans the knowledge_base directory, dynamically chunks all corporate policy documents,
    extracts section and departmental metadata, and populates the persistent ChromaDB collection.
    """
    print("🚀 Initializing Enterprise-Scale Multi-Document Vector Ingestion...")

    # 1. Environment & Gemini Configuration
    load_dotenv()
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        return

    genai.configure(api_key=gemini_api_key)
    custom_google_ef = CustomGeminiEmbeddingFunction()

    # 2. Persistent ChromaDB Client Setup
    # Resolving absolute path to avoid directory drift across environments
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_path = os.path.join(base_dir, "chroma_db")
    client = chromadb.PersistentClient(path=chroma_path)
    
    # Get or create the unified company policies collection
    collection = client.get_or_create_collection(
        name="company_policies",
        embedding_function=custom_google_ef
    )

    # 3. Discover All Knowledge Base Text Files
    kb_dir = os.path.join(base_dir, "knowledge_base")
    policy_files = glob.glob(os.path.join(kb_dir, "*.txt"))

    if not policy_files:
        print(f"❌ Error: No .txt policy documents found in {kb_dir}")
        return

    print(f"📂 Discovered {len(policy_files)} policy manuals: {[os.path.basename(f) for f in policy_files]}")

    # 4. Text Splitting Configuration (500 chars with 100 overlap)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", ". ", " "]
    )

    documents = []
    metadatas = []
    ids = []
    total_chunk_counter = 0

    # 5. Multi-Document Parsing & Metadata Injection
    for file_path in policy_files:
        file_name = os.path.basename(file_path)
        # Infer department category from filename (e.g., hr_policies.txt -> HR)
        dept_name = file_name.replace("_policies.txt", "").replace(".txt", "").upper()

        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Split document by Section Headers
        sections = file_content.split("[SECTION ")

        for section in sections:
            if not section.strip():
                continue

            section_title_match = re.match(r"(.*?)]", section)
            if section_title_match:
                section_name = section_title_match.group(1).strip()
                section_body = section.replace(section_title_match.group(0), "").strip()
            else:
                section_name = "General"
                section_body = section.strip()

            chunks = text_splitter.split_text(section_body)

            for chunk_idx, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({
                    "source_file": file_name,
                    "department": dept_name,
                    "section": section_name,
                    "chunk_size": len(chunk)
                })
                # Unique deterministic ID: doc_HR_sec_1_chk_0
                safe_sec_id = section_name.split(':')[0].strip().replace(" ", "_")
                ids.append(f"doc_{dept_name}_{safe_sec_id}_chk_{chunk_idx}")
                total_chunk_counter += 1

    print(f"\n📚 Total context-aware text chunks generated across all documents: {len(documents)}")
    print("Initiating 3072-Dimensional Gemini embedding generation and Vector DB ingestion...")

    # 6. Upsert Embeddings into ChromaDB
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print("\n✅ Enterprise Vector Database Setup Complete!")
    print(f"-> Total indexed records currently in ChromaDB: {collection.count()}")

if __name__ == "__main__":
    setup_vector_database()