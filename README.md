# MediBot: Medical Assistant Chatbot 🩺

MediBot is a medical assistant chatbot that uses Retrieval-Augmented Generation (RAG) to answer questions based on uploaded documents. It helps users search through medical guides, reports, and manuals to get clear answers with source citations.

---

## How It Works

### 1. Document Upload (Ingestion)
- **File Check:** When you upload a PDF, the system checks if it is a medical document and rejects it if it is not.
- **PII Redaction:** It automatically searches for and removes personal information (like phone numbers and Social Security Numbers) to protect privacy.
- **Chunking & Saving:** It cleans up formatting issues, splits the text into small pieces (chunks), creates vector embeddings, and saves them into the Pinecone database.

### 2. Asking Questions (Query & Retrieval)
- **Query Optimization:** The system automatically cleans up spelling and wording in your question to get better search results.
- **Search & Rank:** It searches the Pinecone database for matching chunks, ranks them to find the most relevant ones, and filters out low-relevance results.
- **Answering:** It sends the best matching chunks to Google Gemini to write a clear response based *only* on the document content.
- **Sources & Confidence:** Along with the answer, it displays a confidence score and links back to the specific PDF name and page number.

---

## Technologies Used

- **Frontend:** HTML, JavaScript, and Tailwind CSS.
- **Backend:** FastAPI (Python web framework).
- **AI Models & API:**
  - **Google Gemini:** For document validation, question optimization, and answer generation.
  - **Pinecone:** For storing and searching document text chunks.
  - **HuggingFace Models:** Local models used to calculate similarity and rank search results.

---

## Folder Structure

```text
medicalAssistant/
├── client/                  # Web Frontend (HTML, CSS, JS)
│   ├── index.html           # Main user interface
│   └── app.js               # API requests and UI logic
├── server/                  # FastAPI Backend (Python)
│   ├── routes/              # API endpoints (/ask and /upload)
│   ├── modules/             # Code for cleaning, chunking, and querying
│   ├── uploaded_docs/       # Folder where PDFs are processed
│   ├── .env                 # API Keys (Google, Pinecone, etc.)
│   ├── requirements.txt     # Python packages needed
│   └── main.py              # Server entry point
├── assets/                  # Sample documents for testing
├── .gitignore               # List of files to ignore in Git
├── main.py                  # Entrypoint runner script
└── pyproject.toml           # Project configuration metadata
```

---

## Setup & Running the Project

### Prerequisites
- Python 3.10 or higher
- A Pinecone Index (384 dimensions, Cosine metric)
- A Google Gemini API Key

### 1. Setting Up the Backend
1. Go to the `server/` directory:
   ```bash
   cd server
   ```
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - **Windows:** `.venv\Scripts\activate`
   - **macOS/Linux:** `source .venv/bin/activate`
4. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a file named `.env` in the `server/` directory and add your API keys:
   ```ini
   GOOGLE_API_KEY=your_gemini_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_INDEX_NAME=medicalindex
   ```
6. Start the backend server:
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

### 2. Running the Frontend
1. Open the `client/index.html` file in your web browser.
2. Alternatively, serve it using Python:
   ```bash
   python -m http.server 3000 --directory client
   ```
   Then open `http://localhost:3000` in your web browser.
