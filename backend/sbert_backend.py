from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
import numpy as np
import os
from typing import List, Dict, Any
import uuid
import logging
import re
from collections import Counter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Plagiarism Detection System - Sentence-BERT",
    version="2.0.0",
    description="Plagiarism detection with lightweight text summarization",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MODEL LOADING ====================

print("🚀 Starting Enhanced Plagiarism Detection System...")
print("📦 Loading Sentence-BERT model...")

try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Sentence-BERT model loaded successfully!")
    print("💾 Model size: ~80MB (optimized for production)")
except Exception as e:
    print(f"❌ Error loading Sentence-BERT model: {e}")
    import sys
    sys.exit(1)

print("📊 System ready with core features!")
print("=" * 50)

# ==================== PYDANTIC MODELS ====================

class SimilarityRequest(BaseModel):
    text1: str
    text2: str

class PlagiarismResponse(BaseModel):
    similarity_score: float
    is_plagiarized: bool
    threshold: float = 0.8
    message: str

class BatchAnalysisResponse(BaseModel):
    results: List[Dict[str, Any]]
    average_similarity: float
    plagiarism_count: int

class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 150
    min_length: int = 30

class SummarizeResponse(BaseModel):
    original_length: int
    summary: str
    summary_length: int
    compression_ratio: float
    method: str = "extractive"

class FAQ(BaseModel):
    question: str
    answer: str
    category: str = "General"

# ==================== TEXT SUMMARIZATION FUNCTIONS ====================

def simple_extractive_summarization(text, max_sentences=3):
    """Simple extractive summarization using sentence scoring"""
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if len(sentences) <= 1:
        return text[:200] + "..." if len(text) > 200 else text
    
    # Simple scoring: longer sentences with important words get higher scores
    important_words = ['important', 'key', 'main', 'primary', 'significant', 
                      'conclusion', 'result', 'find', 'show', 'demonstrate',
                      'summary', 'purpose', 'goal', 'objective', 'method',
                      'result', 'finding', 'conclusion', 'recommendation']
    
    scores = []
    for sentence in sentences:
        score = 0
        # Score based on length (but not too long)
        score += min(len(sentence.split()), 30) * 0.5
        
        # Score based on important words
        lower_sentence = sentence.lower()
        for word in important_words:
            if word in lower_sentence:
                score += 10
        
        # Score based on position (first and last sentences are often important)
        scores.append(score)
    
    # Get top sentences
    top_indices = np.argsort(scores)[-max_sentences:]
    top_indices = sorted(top_indices)
    
    # Combine top sentences
    summary = ' '.join([sentences[i] for i in top_indices])
    
    return summary

def tfidf_based_summarization(text, max_sentences=3):
    """TF-IDF based summarization using simple word frequency"""
    
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if len(sentences) <= 1:
        return text[:200] + "..." if len(text) > 200 else text
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                  'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 
                  'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did'}
    
    # Calculate word frequencies
    word_freq = Counter()
    for sentence in sentences:
        words = re.findall(r'\b\w+\b', sentence.lower())
        words = [w for w in words if w not in stop_words and len(w) > 2]
        word_freq.update(words)
    
    # Score sentences based on word frequencies
    scores = []
    for sentence in sentences:
        score = 0
        words = re.findall(r'\b\w+\b', sentence.lower())
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        for word in words:
            score += word_freq[word]
        
        # Normalize by sentence length
        if len(words) > 0:
            score = score / len(words)
        
        scores.append(score)
    
    # Get top sentences
    top_indices = np.argsort(scores)[-max_sentences:]
    top_indices = sorted(top_indices)
    
    summary = ' '.join([sentences[i] for i in top_indices])
    
    return summary

def summarize_text_simple(text, max_length=150, min_length=30):
    """Main summarization function using simple algorithms"""
    
    # Clean the text
    text = text.strip()
    if not text:
        return "No text provided for summarization."
    
    # Choose summarization method based on text length
    if len(text.split()) < 30:
        # For very short texts, just return the text
        return text[:max_length]
    
    # Try TF-IDF method first
    summary = tfidf_based_summarization(text, max_sentences=3)
    
    # If summary is too short, try the simpler method
    if len(summary.split()) < min_length / 3:
        summary = simple_extractive_summarization(text, max_sentences=4)
    
    # Ensure summary is within bounds
    words = summary.split()
    if len(words) > max_length / 5:  # Approximate word count
        summary = ' '.join(words[:int(max_length / 5)])
    
    # Add ellipsis if heavily truncated
    if len(summary) < len(text) * 0.3:
        summary = summary.strip()
        if not summary.endswith('...'):
            summary += '...'
    
    return summary

# ==================== DATA STORAGE ====================

documents_db = {}

# Pre-defined FAQs
RESEARCH_FAQS = [
    FAQ(
        question="What is the research objective?",
        answer="To compare text similarity methods (TF-IDF vs Sentence-BERT) for duplicate document detection across multiple domains.",
        category="Research"
    ),
    FAQ(
        question="What datasets were used?",
        answer="Stack Overflow Q&A pairs, Quora duplicate questions, and academic abstract pairs.",
        category="Data"
    ),
    FAQ(
        question="What were the key findings?",
        answer="Sentence-BERT achieved 218.3% improvement on Stack Overflow and 155.2% improvement on academic texts compared to TF-IDF.",
        category="Results"
    ),
    FAQ(
        question="What is Sentence-BERT?",
        answer="Sentence-BERT (SBERT) is a modification of BERT that uses siamese networks to generate semantically meaningful sentence embeddings.",
        category="Technology"
    ),
    FAQ(
        question="What is TF-IDF?",
        answer="Term Frequency-Inverse Document Frequency is a statistical measure for evaluating word importance in documents.",
        category="Technology"
    ),
    FAQ(
        question="How does the plagiarism detection work?",
        answer="It uses Sentence-BERT to convert texts into semantic vectors and calculates cosine similarity between them.",
        category="System"
    ),
    FAQ(
        question="What similarity threshold indicates plagiarism?",
        answer="Similarity scores above 0.8 (80%) are flagged as potential plagiarism based on research findings.",
        category="System"
    ),
    FAQ(
        question="How does text summarization work?",
        answer="The system uses extractive summarization based on sentence importance scoring and TF-IDF.",
        category="Features"
    ),
]

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Enhanced Plagiarism Detection System",
        "version": "2.0.0",
        "status": "operational",
        "features": ["Plagiarism Detection", "Text Summarization", "Research FAQs"],
        "endpoints": {
            "compare_texts": "POST /api/similarity/compare",
            "summarize_text": "POST /api/summarize",
            "get_faqs": "GET /api/faqs",
            "upload_document": "POST /api/documents/upload",
            "check_plagiarism": "POST /api/documents/{id}/check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "plagiarism-detector",
        "timestamp": np.datetime64('now').astype(str),
        "features": {
            "similarity": True,
            "summarization": True
        }
    }

@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "endpoints": {
            "compare_texts": "POST /api/similarity/compare",
            "summarize_text": "POST /api/summarize",
            "get_faqs": "GET /api/faqs",
            "upload_document": "POST /api/documents/upload",
            "list_documents": "GET /api/documents",
            "check_plagiarism": "POST /api/documents/{id}/check",
            "delete_document": "DELETE /api/documents/{id}"
        },
        "models": {
            "similarity": "all-MiniLM-L6-v2 (80MB)",
            "summarization": "Extractive summarization (rule-based)"
        },
        "similarity_threshold": 0.8
    }

# ==================== SIMILARITY ENDPOINTS ====================

@app.post("/api/similarity/compare", response_model=PlagiarismResponse)
async def compare_texts(request: SimilarityRequest):
    """Compare two texts using Sentence-BERT"""
    try:
        logger.info(f"Comparing texts...")
        
        # Encode the texts
        embeddings = model.encode([request.text1, request.text2], convert_to_tensor=True)
        
        # Calculate cosine similarity
        cosine_scores = util.cos_sim(embeddings[0], embeddings[1])
        similarity_score = float(cosine_scores[0][0])
        
        # Determine if plagiarized
        is_plagiarized = similarity_score > 0.8
        
        message = "High semantic similarity detected - potential plagiarism" if is_plagiarized else "Low semantic similarity - likely original content"
        
        return PlagiarismResponse(
            similarity_score=similarity_score,
            is_plagiarized=is_plagiarized,
            message=message
        )
    
    except Exception as e:
        logger.error(f"Error comparing texts: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing texts: {str(e)}")

# ==================== SUMMARIZATION ENDPOINTS ====================

@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize_text(request: SummarizeRequest):
    """Summarize text using simple extractive methods"""
    try:
        # Validate input
        text = request.text.strip()
        if len(text) < 20:
            raise HTTPException(
                status_code=400, 
                detail="Text is too short for summarization (minimum 20 characters)"
            )
        
        logger.info(f"Summarizing text of length: {len(text)}")
        
        # Generate summary using simple method
        summary = summarize_text_simple(
            text, 
            max_length=request.max_length,
            min_length=request.min_length
        )
        
        # Ensure summary is not empty
        if not summary or len(summary.strip()) == 0:
            summary = "Unable to generate summary. The text may be too short or complex."
        
        # Calculate metrics
        compression_ratio = len(summary) / len(text) if len(text) > 0 else 0
        
        logger.info(f"Summarization complete: {len(summary)} chars (compression: {compression_ratio:.2%})")
        
        return SummarizeResponse(
            original_length=len(request.text),
            summary=summary,
            summary_length=len(summary),
            compression_ratio=compression_ratio,
            method="extractive"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in summarization: {e}")
        # Fallback: return first 200 characters
        fallback_summary = request.text[:200] + "..." if len(request.text) > 200 else request.text
        return SummarizeResponse(
            original_length=len(request.text),
            summary=fallback_summary,
            summary_length=len(fallback_summary),
            compression_ratio=len(fallback_summary) / len(request.text) if len(request.text) > 0 else 0,
            method="fallback"
        )

# ==================== FAQ ENDPOINTS ====================

@app.get("/api/faqs")
async def get_faqs(category: str = None):
    """Get frequently asked questions"""
    if category and category.lower() != "all":
        filtered_faqs = [faq for faq in RESEARCH_FAQS if faq.category.lower() == category.lower()]
        categories = list(set([faq.category for faq in filtered_faqs]))
        return {
            "faqs": filtered_faqs, 
            "total": len(filtered_faqs), 
            "category": category,
            "categories": categories
        }
    
    all_categories = list(set([faq.category for faq in RESEARCH_FAQS]))
    return {
        "faqs": RESEARCH_FAQS, 
        "total": len(RESEARCH_FAQS), 
        "categories": all_categories
    }

@app.post("/api/faqs/add")
async def add_faq(faq: FAQ):
    """Add a new FAQ"""
    RESEARCH_FAQS.append(faq)
    logger.info(f"New FAQ added: {faq.question}")
    return {
        "message": "FAQ added successfully", 
        "total": len(RESEARCH_FAQS),
        "faq": faq
    }

# ==================== DOCUMENT ENDPOINTS ====================

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document"""
    try:
        content = await file.read()
        text = content.decode('utf-8')
        
        doc_id = str(uuid.uuid4())
        
        documents_db[doc_id] = {
            "filename": file.filename,
            "text": text,
            "size": len(text),
            "upload_time": np.datetime64('now').astype(str)
        }
        
        logger.info(f"Document uploaded: {file.filename}")
        
        return {
            "document_id": doc_id,
            "filename": file.filename,
            "size": len(text),
            "message": "Document uploaded successfully"
        }
    
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@app.post("/api/documents/{document_id}/check")
async def check_document_plagiarism(document_id: str):
    """Check document for plagiarism"""
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    target_doc = documents_db[document_id]
    logger.info(f"Checking plagiarism for document: {target_doc['filename']}")
    
    target_embedding = model.encode([target_doc["text"]], convert_to_tensor=True)[0]
    
    results = []
    
    for doc_id, document in documents_db.items():
        if doc_id == document_id:
            continue
        
        doc_embedding = model.encode([document["text"]], convert_to_tensor=True)[0]
        similarity_score = float(util.cos_sim(target_embedding, doc_embedding)[0][0])
        
        results.append({
            "document_id": doc_id,
            "filename": document["filename"],
            "similarity_score": similarity_score,
            "is_plagiarized": similarity_score > 0.8
        })
    
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    plagiarism_count = sum(1 for result in results if result["is_plagiarized"])
    average_similarity = np.mean([result["similarity_score"] for result in results]) if results else 0
    
    logger.info(f"Plagiarism check completed: {plagiarism_count} potential matches")
    
    return BatchAnalysisResponse(
        results=results,
        average_similarity=average_similarity,
        plagiarism_count=plagiarism_count
    )

@app.get("/api/documents")
async def list_documents():
    """List all uploaded documents"""
    documents_list = [
        {
            "document_id": doc_id,
            "filename": doc["filename"],
            "size": doc["size"],
            "upload_time": doc.get("upload_time", "unknown")
        }
        for doc_id, doc in documents_db.items()
    ]
    
    logger.info(f"Listing {len(documents_list)} documents")
    
    return {
        "documents": documents_list,
        "total_count": len(documents_list)
    }

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    filename = documents_db[document_id]["filename"]
    del documents_db[document_id]
    
    logger.info(f"Document deleted: {filename}")
    
    return {"message": "Document deleted successfully"}

# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": f"Resource not found. Available endpoints: /api/similarity/compare, /api/summarize, /api/faqs, /api/documents/upload"}
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

# ==================== SERVER STARTUP ====================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"🎯 Starting Enhanced Plagiarism Detection Server")
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"📚 API Documentation: http://0.0.0.0:{port}/docs")
    print(f"❤️  Health Check: http://0.0.0.0:{port}/health")
    print(f"🔬 Core Model: Sentence-BERT")
    print(f"📊 Features: Plagiarism Detection, Text Summarization, Research FAQs")
    print(f"⚡ Summarization: Lightweight extractive method (no heavy models)")
    print(f"💾 Memory: Optimized for free tier deployment")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )