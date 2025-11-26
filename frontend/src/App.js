import React, { useState, useEffect } from 'react';
import './App.css';

// Use your Render backend URL
const API_BASE_URL = 'https://plagiarism-detection-system-3.onrender.com';

function App() {
  const [activeTab, setActiveTab] = useState('compare');
  const [text1, setText1] = useState('');
  const [text2, setText2] = useState('');
  const [similarityResult, setSimilarityResult] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [checkResults, setCheckResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');

  // Compare two texts
  const compareTexts = async () => {
    if (!text1.trim() || !text2.trim()) {
      alert('Please enter both texts to compare');
      return;
    }

    setLoading(true);
    try {
      console.log('Sending request to:', `${API_BASE_URL}/api/similarity/compare`);
      
      const response = await fetch(`${API_BASE_URL}/api/similarity/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text1, text2 })
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Response data:', result);
      setSimilarityResult(result);
      
    } catch (error) {
      console.error('Error details:', error);
      alert(`Error comparing texts: ${error.message}. Make sure the backend is running on ${API_BASE_URL}`);
    } finally {
      setLoading(false);
    }
  };

  // Upload document - FIXED VERSION USING FormData
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Only text files for this version
    if (!file.type.includes('text') && !file.name.endsWith('.txt')) {
      alert('Please upload a text file (.txt)');
      return;
    }

    setLoading(true);
    try {
      console.log('Uploading file:', file.name);
      
      // Use FormData instead of JSON - this fixes the 422 error
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: 'POST',
        body: formData
        // Remove Content-Type header - browser sets it automatically for FormData
      });
      
      console.log('Upload response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.log('Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Upload success:', result);
      
      setUploadMessage(`Document "${result.filename}" uploaded successfully!`);
      loadDocuments();
      event.target.value = ''; // Reset file input
      
    } catch (error) {
      console.error('Upload error details:', error);
      setUploadMessage(`Error uploading document: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Load all documents
  const loadDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  // Check document for plagiarism
  const checkDocument = async (documentId) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      setCheckResults(result);
    } catch (error) {
      console.error('Error checking document:', error);
      alert('Error checking document for plagiarism');
    } finally {
      setLoading(false);
    }
  };

  // Delete document
  const deleteDocument = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setUploadMessage('Document deleted successfully!');
        loadDocuments();
        setCheckResults(null);
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Error deleting document');
    }
  };

  // Load documents when tab changes
  useEffect(() => {
    if (activeTab === 'documents') {
      loadDocuments();
    }
  }, [activeTab]);

  return (
    <div className="App">
      <header className="app-header">
        <h1>Plagiarism Detection System</h1>
        <p>A Comparative Analysis of Text Similarity Methods for Duplicate Document Detection</p>
      </header>

      <nav className="tab-navigation">
        <button 
          className={activeTab === 'compare' ? 'active' : ''} 
          onClick={() => setActiveTab('compare')}
        >
          Compare Texts
        </button>
        <button 
          className={activeTab === 'documents' ? 'active' : ''} 
          onClick={() => setActiveTab('documents')}
        >
          Document Management
        </button>
      </nav>

      <main className="main-content">
        {activeTab === 'compare' && (
          <div className="compare-section">
            <h2>Compare Two Texts</h2>
            <div className="text-inputs">
              <div className="text-area-container">
                <h3>Text 1</h3>
                <textarea
                  value={text1}
                  onChange={(e) => setText1(e.target.value)}
                  placeholder="Enter first text here..."
                  rows="10"
                />
              </div>
              <div className="text-area-container">
                <h3>Text 2</h3>
                <textarea
                  value={text2}
                  onChange={(e) => setText2(e.target.value)}
                  placeholder="Enter second text here..."
                  rows="10"
                />
              </div>
            </div>
            
            <button 
              onClick={compareTexts} 
              disabled={loading}
              className="compare-button"
            >
              {loading ? 'Analyzing...' : 'Compare Texts'}
            </button>

            {similarityResult && (
              <div className={`result-card ${similarityResult.is_plagiarized ? 'plagiarized' : 'original'}`}>
                <h3>Similarity Analysis Result</h3>
                <div className="score-display">
                  <span className="score-label">Similarity Score:</span>
                  <span className="score-value">{(similarityResult.similarity_score * 100).toFixed(2)}%</span>
                </div>
                <div className="verdict">
                  <strong>Verdict:</strong> {similarityResult.message}
                </div>
                <div className="threshold-info">
                  Threshold for plagiarism: {(similarityResult.threshold * 100).toFixed(0)}%
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="documents-section">
            <h2>Document Management</h2>
            
            {uploadMessage && (
              <div className={`message-banner ${uploadMessage.includes('Error') ? 'error' : 'success'}`}>
                {uploadMessage}
              </div>
            )}
            
            <div className="upload-section">
              <h3>Upload Document</h3>
              <input
                type="file"
                onChange={handleFileUpload}
                accept=".txt"
                disabled={loading}
              />
              <p>Supported format: TXT files only</p>
            </div>

            <div className="documents-list">
              <h3>Uploaded Documents ({documents.length})</h3>
              {documents.length === 0 ? (
                <p>No documents uploaded yet.</p>
              ) : (
                <div className="document-cards">
                  {documents.map(doc => (
                    <div key={doc.document_id} className="document-card">
                      <div className="doc-info">
                        <strong>{doc.filename}</strong>
                        <span>Size: {doc.size} characters</span>
                      </div>
                      <div className="doc-actions">
                        <button 
                          onClick={() => checkDocument(doc.document_id)}
                          disabled={loading}
                          className="check-button"
                        >
                          Check Plagiarism
                        </button>
                        <button 
                          onClick={() => deleteDocument(doc.document_id)}
                          className="delete-button"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {checkResults && (
              <div className="check-results">
                <h3>Plagiarism Check Results</h3>
                <div className="summary">
                  <p>Average Similarity: {(checkResults.average_similarity * 100).toFixed(2)}%</p>
                  <p>Potential Plagiarism Cases: {checkResults.plagiarism_count}</p>
                </div>
                
                <div className="similarity-list">
                  {checkResults.results.map(result => (
                    <div 
                      key={result.document_id} 
                      className={`similarity-item ${result.is_plagiarized ? 'high-similarity' : ''}`}
                    >
                      <div className="similarity-doc">
                        <strong>{result.filename}</strong>
                        <span>{(result.similarity_score * 100).toFixed(2)}% similar</span>
                      </div>
                      {result.is_plagiarized && (
                        <span className="plagiarism-warning">⚠️ Potential Plagiarism</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by Sentence-BERT | Research- Text Similarity Methods</p>
      </footer>
    </div>
  );
}

export default App;