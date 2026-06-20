from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from modules.llm import get_llm_chain
from modules.query_handlers import query_chain
from langchain_core.documents import Document
from langchain.schema import BaseRetriever
from langchain_community.embeddings import HuggingFaceEmbeddings
from pinecone import Pinecone
from pydantic import Field
from typing import List, Optional
from logger import logger
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from sentence_transformers import CrossEncoder
import math

router=APIRouter()

def rewrite_query(query: str) -> str:
    """Query Transformation: Rewrites user query into a clean search term."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: return query
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key, temperature=0.0)
    prompt = f"You are a medical search optimizer. Rewrite the following user query to fix any spelling errors and make it a clean, direct search query. Do NOT make it overly complex or academic. Keep it simple.\n\nOriginal: {query}\n\nRewritten:"
    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception:
        return query

class SimpleRetriever(BaseRetriever):
    docs: List[Document]

    def _get_relevant_documents(self, query: str) -> List[Document]:
        return self.docs

from pydantic import BaseModel

class QuestionRequest(BaseModel):
    question: str

@router.post("/ask/")
async def ask_question(request: QuestionRequest):
    question = request.question
    try:
        logger.info(f"user query: {question}")

        # 🌟 ELITE UPGRADE 1: Query Rewriting
        rewritten_query = rewrite_query(question)
        logger.info(f"[REWRITE] Original: '{question}' -> Rewritten: '{rewritten_query}'")

        # Pinecone setup
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index_name = os.getenv("PINECONE_INDEX_NAME", "medicalindex")
        index = pc.Index(index_name)
        
        # Local Embeddings
        embed_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        embedded_query = embed_model.embed_query(rewritten_query)
        
        # 🌟 ELITE UPGRADE 2: Retrieve Top 15 (Broad Search)
        logger.info("[RETRIEVE] Fetching top 15 chunks from Pinecone...")
        res = index.query(vector=embedded_query, top_k=15, include_metadata=True)
        
        # 🌟 ELITE UPGRADE 3: Fallback Handling
        if not res["matches"]:
            logger.warning("[FALLBACK] No chunks found in Pinecone.")
            return {"answer": "No relevant information found in the uploaded document.", "confidence": 0, "sources": []}

        # 🌟 ELITE UPGRADE 4: Re-Ranking Layer
        logger.info("[RE-RANK] Scoring 15 chunks with Cross-Encoder...")
        cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        texts = [match["metadata"].get("text", "") for match in res["matches"]]
        pairs = [[rewritten_query, text] for text in texts]
        scores = cross_encoder.predict(pairs)
        
        scored_matches = list(zip(res["matches"], scores))
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        
        top_score = float(scored_matches[0][1])
        # Convert logit to pseudo-probability % (centered around the -2.0 threshold)
        confidence_pct = round((1 / (1 + math.exp(-(top_score + 2.0)))) * 100)
        
        # 🌟 ELITE UPGRADE 5: Context Filtering Guard
        if top_score < -2.0: # ms-marco threshold
            logger.warning(f"[FALLBACK] Top score {top_score} is below confidence threshold.")
            return {"answer": "I could not find a confident answer based on the uploaded documents. Please verify with a medical professional.", "confidence": confidence_pct, "sources": []}

        # Select Top 4 Best Chunks
        top_4_matches = [m[0] for m in scored_matches[:4]]
        
        sources = []
        docs = []
        for match in top_4_matches:
            text = match["metadata"].get("text", "")
            source_name = match["metadata"].get("source", "Unknown Document")
            page = match["metadata"].get("page", 0)
            
            # Extract filename from path if necessary
            clean_source = os.path.basename(source_name)
            
            docs.append(Document(page_content=text, metadata=match["metadata"]))
            sources.append({
                "document": clean_source,
                "page": page,
                "text": text[:100] + "..."
            })

        retriever = SimpleRetriever(docs=docs)
        chain = get_llm_chain(retriever)
        
        logger.info("[GENERATE] Sending top 4 filtered chunks to Gemini...")
        raw_result = query_chain(chain, rewritten_query)
        
        if isinstance(raw_result, dict):
            final_answer = raw_result.get("result") or raw_result.get("response") or raw_result.get("answer") or str(raw_result)
        else:
            final_answer = raw_result
        
        # 🌟 ELITE UPGRADE 6: Source Citations Output
        result = {
            "answer": final_answer,
            "confidence": confidence_pct,
            "sources": sources
        }

        logger.info(f"[SUCCESS] Query complete with {confidence_pct}% confidence.")
        return result

    except Exception as e:
        logger.exception("Error processing question")
        error_msg = str(e)
        if "429" in error_msg or "Quota exceeded" in error_msg:
            error_msg = "Google API Rate Limit Exceeded (15 RPM). Please wait 60 seconds."
        return JSONResponse(status_code=500, content={"error": error_msg})