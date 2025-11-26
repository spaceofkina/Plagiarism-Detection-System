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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(title="Plagiarism Detection System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load SBERT model
print("Starting to load Sentence-BERT model...")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Using smaller model
    print("✓ Model loaded successfully!")
except Exception as e:
    print(f"✗ Error loading model: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

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

# Store documents in memory
documents_db = {}

@app.get("/")
async def root():
    return {"message": "Plagiarism Detection System API", "version": "1.0.0"}

@app.post("/api/similarity/compare", response_model=PlagiarismResponse)
async def compare_texts(request: SimilarityRequest):
    """
    Compare two texts and return similarity score
    """
    try:
        # Encode the texts
        embeddings = model.encode([request.text1, request.text2], convert_to_tensor=True)
        
        # Calculate cosine similarity
        cosine_scores = util.cos_sim(embeddings[0], embeddings[1])
        similarity_score = float(cosine_scores[0][0])
        
        # Determine if plagiarized (threshold based on research findings)
        is_plagiarized = similarity_score > 0.8
        
        message = "High similarity detected - potential plagiarism" if is_plagiarized else "Low similarity - likely original content"
        
        return PlagiarismResponse(
            similarity_score=similarity_score,
            is_plagiarized=is_plagiarized,
            message=message
        )
    
    except Exception as e:
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
            "size": len(text)
        }
        
        return {
            "document_id": doc_id,
            "filename": file.filename,
            "size": len(text),
            "message": "Document uploaded successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@app.post("/api/documents/{document_id}/check")
async def check_document_plagiarism(document_id: str):
    """
    Check a document against all other documents for plagiarism
    """
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    target_doc = documents_db[document_id]
    target_embedding = model.encode([target_doc["text"]], convert_to_tensor=True)[0]
    
    results = []
    
    for doc_id, document in documents_db.items():
        if doc_id == document_id:
            continue  # Skip self-comparison
        
        # Calculate similarity
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
    return {
        "documents": [
            {
                "document_id": doc_id,
                "filename": doc["filename"],
                "size": doc["size"]
            }
            for doc_id, doc in documents_db.items()
        ]
    }

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document
    """
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    del documents_db[document_id]
    return {"message": "Document deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Plagiarism Detection Server on http://localhost:8001")
    print("📚 API Documentation: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)