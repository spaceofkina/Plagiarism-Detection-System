from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import uuid
from typing import List, Dict, Any
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Plagiarism Detection System", version="1.0.0")

# CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use smaller model for production
model = None

def load_model():
    global model
    if model is None:
        print("🚀 Loading Sentence-BERT model (production version)...")
        try:
            from sentence_transformers import SentenceTransformer, util
            # Use smaller, faster model for production
            model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Production model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    return model

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

documents_db = {}

@app.get("/")
async def root():
    return {"message": "Plagiarism Detection System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "plagiarism-detector"}

@app.post("/api/similarity/compare", response_model=PlagiarismResponse)
async def compare_texts(request: SimilarityRequest):
    try:
        model_instance = load_model()
        from sentence_transformers import util
        
        embeddings = model_instance.encode([request.text1, request.text2])
        cosine_scores = util.cos_sim(embeddings[0], embeddings[1])
        similarity_score = float(cosine_scores[0][0])
        
        is_plagiarized = similarity_score > 0.8
        message = "High semantic similarity - potential plagiarism" if is_plagiarized else "Low similarity - likely original"
        
        return PlagiarismResponse(
            similarity_score=similarity_score,
            is_plagiarized=is_plagiarized,
            message=message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = content.decode('utf-8')
        doc_id = str(uuid.uuid4())
        
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/{document_id}/check")
async def check_document_plagiarism(document_id: str):
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    target_doc = documents_db[document_id]
    model_instance = load_model()
    from sentence_transformers import util
    
    target_embedding = model_instance.encode([target_doc["text"]])[0]
    
    results = []
    
    for doc_id, document in documents_db.items():
        if doc_id == document_id:
            continue
        
        doc_embedding = model_instance.encode([document["text"]])[0]
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
    
    return BatchAnalysisResponse(
        results=results,
        average_similarity=average_similarity,
        plagiarism_count=plagiarism_count
    )

@app.get("/api/documents")
async def list_documents():
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
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    del documents_db[document_id]
    return {"message": "Document deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🎯 Starting Production Server on port {port}")
    print(f"🔬 Using: all-MiniLM-L6-v2 (optimized for production)")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")