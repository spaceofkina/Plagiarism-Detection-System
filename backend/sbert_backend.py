from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
import numpy as np
import tempfile
import os
from typing import List, Dict, Any
import uuid
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This ensures logs go to Render's output
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Plagiarism Detection System - Sentence-BERT",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - allow all origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load SBERT model with error handling and progress logging
print("🚀 Starting Plagiarism Detection System...")
print("📦 Loading Sentence-BERT model...")

try:
    # Use the same model from your research paper
    model = SentenceTransformer('all-mpnet-base-v2')
    print("✅ Sentence-BERT model loaded successfully!")
    print(f"🔧 Model device: cpu")  # Render uses CPU
    print("📊 Ready for semantic similarity detection")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    logger.error(f"Model loading failed: {e}")
    # Exit if model fails to load
    import sys
    sys.exit(1)

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

# Store documents in memory (for demo - in production use a database)
documents_db = {}

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Plagiarism Detection System with Sentence-BERT",
        "version": "1.0.0",
        "status": "operational",
        "model": "all-mpnet-base-v2"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render monitoring"""
    return {
        "status": "healthy",
        "service": "plagiarism-detector",
        "model_loaded": True,
        "timestamp": np.datetime64('now').astype(str)
    }

@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "endpoints": {
            "compare_texts": "POST /api/similarity/compare",
            "upload_document": "POST /api/documents/upload",
            "list_documents": "GET /api/documents",
            "check_plagiarism": "POST /api/documents/{id}/check",
            "delete_document": "DELETE /api/documents/{id}"
        },
        "model": "all-mpnet-base-v2",
        "similarity_threshold": 0.8
    }

@app.post("/api/similarity/compare", response_model=PlagiarismResponse)
async def compare_texts(request: SimilarityRequest):
    """
    Compare two texts using Sentence-BERT semantic similarity
    """
    try:
        logger.info(f"Comparing texts: '{request.text1[:50]}...' vs '{request.text2[:50]}...'")
        
        # Encode the texts using Sentence-BERT
        embeddings = model.encode([request.text1, request.text2], convert_to_tensor=True)
        
        # Calculate cosine similarity
        cosine_scores = util.cos_sim(embeddings[0], embeddings[1])
        similarity_score = float(cosine_scores[0][0])
        
        # Determine if plagiarized (threshold based on research findings)
        is_plagiarized = similarity_score > 0.8
        
        message = "High semantic similarity detected - potential plagiarism" if is_plagiarized else "Low semantic similarity - likely original content"
        
        logger.info(f"Similarity score: {similarity_score:.4f}, Plagiarism: {is_plagiarized}")
        
        return PlagiarismResponse(
            similarity_score=similarity_score,
            is_plagiarized=is_plagiarized,
            message=message
        )
    
    except Exception as e:
        logger.error(f"Error comparing texts: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing texts: {str(e)}")

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for plagiarism checking
    """
    try:
        # Read file content
        content = await file.read()
        text = content.decode('utf-8')
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Store document
        documents_db[doc_id] = {
            "filename": file.filename,
            "text": text,
            "size": len(text),
            "upload_time": np.datetime64('now').astype(str)
        }
        
        logger.info(f"Document uploaded: {file.filename} (ID: {doc_id})")
        
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
    """
    Check a document against all other documents for plagiarism using Sentence-BERT
    """
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    target_doc = documents_db[document_id]
    logger.info(f"Checking plagiarism for document: {target_doc['filename']}")
    
    # Encode the target document
    target_embedding = model.encode([target_doc["text"]], convert_to_tensor=True)[0]
    
    results = []
    
    for doc_id, document in documents_db.items():
        if doc_id == document_id:
            continue  # Skip self-comparison
        
        # Calculate semantic similarity using Sentence-BERT
        doc_embedding = model.encode([document["text"]], convert_to_tensor=True)[0]
        similarity_score = float(util.cos_sim(target_embedding, doc_embedding)[0][0])
        
        results.append({
            "document_id": doc_id,
            "filename": document["filename"],
            "similarity_score": similarity_score,
            "is_plagiarized": similarity_score > 0.8
        })
    
    # Sort by similarity score (descending)
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    plagiarism_count = sum(1 for result in results if result["is_plagiarized"])
    average_similarity = np.mean([result["similarity_score"] for result in results]) if results else 0
    
    logger.info(f"Plagiarism check completed: {plagiarism_count} potential matches found")
    
    return BatchAnalysisResponse(
        results=results,
        average_similarity=average_similarity,
        plagiarism_count=plagiarism_count
    )

@app.get("/api/documents")
async def list_documents():
    """
    List all uploaded documents
    """
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
    """
    Delete a document
    """
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    filename = documents_db[document_id]["filename"]
    del documents_db[document_id]
    
    logger.info(f"Document deleted: {filename} (ID: {document_id})")
    
    return {"message": "Document deleted successfully"}

# Error handlers
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable (Render provides this)
    port = int(os.getenv("PORT", 8000))
    
    print(f"🎯 Starting Sentence-BERT Plagiarism Detection Server")
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"📚 API Documentation: http://0.0.0.0:{port}/docs")
    print(f"❤️  Health Check: http://0.0.0.0:{port}/health")
    print(f"🔬 Model: all-mpnet-base-v2")
    print(f"⚡ Environment: Production")
    print("=" * 50)
    
    # Start the server
    uvicorn.run(
        app,
        host="0.0.0.0",  # Important: must be 0.0.0.0 for Render
        port=port,
        log_level="info",
        access_log=True
    )