import os
import time
from pathlib import Path
from dotenv import load_dotenv
from tqdm.auto import tqdm
from pinecone import Pinecone, ServerlessSpec
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import TokenTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
import re

load_dotenv()

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "medicalindex")
    
    pc = Pinecone(api_key=api_key)
    
    # Check if index exists
    existing_indexes = [i["name"] for i in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"🚀 Creating new Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=384,  # HuggingFace all-MiniLM-L6-v2 dimension
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)
    
    return pc.Index(index_name)

def clean_text(text: str) -> str:
    """OCR Noise Removal & Text Normalization"""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Fix broken hyphens across newlines
    text = re.sub(r'-\s*\n\s*', '', text)
    # Remove null bytes or garbage characters
    text = text.replace('\x00', '')
    return text.strip()

def anonymize_text(text: str) -> str:
    """Basic PII Anonymization (Privacy Layer)"""
    # Scrub Phone Numbers
    text = re.sub(r'\(?\b[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', '[REDACTED_PHONE]', text)
    # Scrub SSNs
    text = re.sub(r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b', '[REDACTED_SSN]', text)
    # Scrub Emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '[REDACTED_EMAIL]', text)
    # For a full production app, integrate Microsoft Presidio here for Names and Addresses
    return text

def triage_document(text_sample: str):
    """Zero-Shot Classification to reject non-medical files (Data Validation Layer)"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return # Skip if no key
        
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key, temperature=0.0)
    
    prompt = f"""
    Analyze the following text sample from an uploaded document. 
    Is this a clinical, medical, health-related document, lab report, or medical research paper? 
    Reply ONLY with YES or NO. Do not explain.
    
    Text Sample:
    {text_sample[:1500]}
    """
    
    response = llm.invoke(prompt)
    result = response.content.strip().upper()
    
    if "NO" in result:
        raise ValueError("NON_MEDICAL_DOCUMENT")

def load_vectorstore(uploaded_files):    
    try:
        index = get_pinecone_index()
        print(f"✅ Connected to Pinecone index: {os.getenv('PINECONE_INDEX_NAME', 'medicalindex')}")
    except Exception as e:
        print(f"❌ Pinecone Connection Error: {e}")
        raise e

    # Use local HuggingFace embeddings (No API key needed!)
    embed_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    file_paths = []
    for file in uploaded_files:
        save_path = Path(UPLOAD_DIR) / file.filename
        with open(save_path, "wb") as f:
            f.write(file.file.read())
        file_paths.append(str(save_path))

    for file_path in file_paths:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # 🌟 INNOVATION 1: Document Triage
        if len(documents) > 0:
            print("🧠 Running Zero-Shot Triage...")
            triage_document(documents[0].page_content)
            
        # 🌟 INNOVATION 2: PII Anonymization & Cleaning
        for doc in documents:
            doc.page_content = clean_text(doc.page_content)
            doc.page_content = anonymize_text(doc.page_content)

        # 🌟 ELITE UPGRADE: Token-Based Chunking
        print("🧠 Chunking text into tokens...")
        splitter = TokenTextSplitter(chunk_size=150, chunk_overlap=20)        
        chunks = splitter.split_documents(documents)

        texts = [chunk.page_content for chunk in chunks]
        
        metadatas = []
        for chunk in chunks:
            m = chunk.metadata.copy()
            m["text"] = chunk.page_content
            metadatas.append(m)
            
        ids = [f"{Path(file_path).stem}-{i}" for i in range(len(chunks))]

        print(f"🔍 Embedding {len(texts)} chunks locally...")
        embeddings = embed_model.embed_documents(texts)

        # 🌟 ELITE UPGRADE: Batched Upserts with basic Exponential Backoff
        print("📤 Uploading to Pinecone in batches...")
        batch_size = 100
        vectors = list(zip(ids, embeddings, metadatas))
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            retries = 3
            for attempt in range(retries):
                try:
                    index.upsert(vectors=batch)
                    print(f"   ✅ Upserted batch {i//batch_size + 1}")
                    break
                except Exception as e:
                    if attempt < retries - 1:
                        sleep_time = 2 ** attempt
                        print(f"   ⚠️ Upsert failed, retrying in {sleep_time}s... Error: {e}")
                        time.sleep(sleep_time)
                    else:
                        print(f"   ❌ DEAD-LETTER: Failed to upsert batch {i//batch_size + 1}. Logging to dead_letter.txt")
                        with open("dead_letter.txt", "a") as dl_file:
                            dl_file.write(f"Failed batch IDs: {[v[0] for v in batch]}\n")

        print(f"✅ Upload complete for {file_path}")
